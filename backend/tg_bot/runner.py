import asyncio
import logging
import os
from datetime import datetime, timezone
from urllib.parse import urlparse

from telegram.ext import Application, CommandHandler, MessageHandler, filters
from telegram.request import HTTPXRequest
from telegram.error import NetworkError, TimedOut

from database import SessionLocal, Base, engine
from models import User

from .config import BOT_CONCURRENT_UPDATES, FAILED_BOT_COOLDOWN, TELEGRAM_CONNECTION_POOL_SIZE
from .db_ops import looks_like_telegram_token, run_db_query
from .monitoring import health_check_loop, log_technical_error_sync
from .net import auto_decide_trust_env_for_telegram, env_truthy, windows_system_proxy_url

logger = logging.getLogger(__name__)

# Global dictionary to track running bots: candidate_id -> Application
running_bots: dict[int, Application] = {}

# candidate_id -> last failure UTC time
failed_bots: dict[int, datetime] = {}


def _telegram_httpx_kwargs() -> dict:
    """Build httpx client kwargs for Telegram API calls.

    Default is direct connection (trust_env=False) unless the user explicitly
    opts into proxy/env behavior.

    - If TELEGRAM_PROXY_URL is set, it is used explicitly (supports socks5/http).
    - Else, TELEGRAM_TRUST_ENV=1 enables inheriting proxy env vars.
    """

    explicit_proxy_url = (os.getenv("TELEGRAM_PROXY_URL") or "").strip()
    if explicit_proxy_url:
        return {"trust_env": False, "proxy": explicit_proxy_url}

    # If user explicitly sets TELEGRAM_TRUST_ENV (even to 0/false), honor it.
    env_val = os.getenv("TELEGRAM_TRUST_ENV")
    if env_val is not None:
        return {"trust_env": env_truthy("TELEGRAM_TRUST_ENV")}

    # Default: do NOT inherit proxy env vars. This avoids flaky/broken Windows proxy setups
    # causing httpx.RemoteProtocolError. If a proxy is required, set TELEGRAM_PROXY_URL or
    # explicitly opt-in via TELEGRAM_TRUST_ENV=1.
    #
    # Windows convenience: if direct connectivity to Telegram is blocked but the user has a
    # system proxy configured (e.g. v2rayN/Clash "Set as system proxy"), automatically
    # fall back to `trust_env=True`.
    auto_raw = os.getenv("TELEGRAM_AUTO_TRUST_ENV")
    auto_enabled = env_truthy("TELEGRAM_AUTO_TRUST_ENV") if auto_raw is not None else (os.name == "nt")
    if auto_enabled:
        try:
            trust_env_val = bool(auto_decide_trust_env_for_telegram())
            if trust_env_val:
                logger.warning(
                    "Direct Telegram connectivity seems unavailable; enabling trust_env=True to use system/environment proxy. "
                    "Set TELEGRAM_TRUST_ENV=0 to force direct mode, or TELEGRAM_PROXY_URL to force a specific proxy."
                )
            return {"trust_env": trust_env_val}
        except Exception:
            return {"trust_env": False}

    return {"trust_env": False}


async def run_bot(candidate: User):
    from .handlers import chatid_command, debug_update_logger, error_handler, handle_message, myid_command, start_command

    import time
    while True:
        try:
            if not candidate.bot_token:
                logger.warning("Candidate %s has no bot token.", candidate.full_name)
                return None

            if not looks_like_telegram_token(candidate.bot_token):
                logger.warning("Candidate %s has an invalid bot token format. Skipping start.", candidate.full_name)
                return None

            logger.info("Starting bot for %s (@%s)...", candidate.full_name, candidate.bot_name)

            bot_config = getattr(candidate, "bot_config", None) or {}

            httpx_kwargs = _telegram_httpx_kwargs()
            using_proxy = bool(httpx_kwargs.get("trust_env")) or bool(httpx_kwargs.get("proxy"))

            # In proxy environments, long-lived tunnels are more likely to be dropped. Keep the
            # long-polling timeout shorter to reduce RemoteProtocolError frequency.
            poll_timeout_raw = (os.getenv("TELEGRAM_POLLING_TIMEOUT") or "").strip()
            if poll_timeout_raw:
                try:
                    poll_timeout = int(poll_timeout_raw)
                except ValueError:
                    poll_timeout = 10
            else:
                poll_timeout = 5 if using_proxy else 10
            if poll_timeout < 1:
                poll_timeout = 1

            # read_timeout must be > poll_timeout because Telegram uses long polling.
            poll_read_timeout = max(30.0, float(poll_timeout + 20))

            def polling_error_callback(exc):
                # Updater will keep retrying in network_retry_loop. For expected, transient proxy
                # disconnects, avoid logging huge tracebacks.
                msg = str(exc) if exc is not None else ""
                if isinstance(exc, NetworkError) and (
                    "RemoteProtocolError" in msg or "Server disconnected without sending a response" in msg
                ):
                    logger.warning(
                        "Telegram polling connection dropped (candidate_id=%s). Will retry: %s",
                        getattr(candidate, "id", None),
                        msg,
                    )
                    return

                logger.error(
                    "Exception happened while polling for updates (candidate_id=%s): %s",
                    getattr(candidate, "id", None),
                    msg,
                    exc_info=exc,
                )
            # --- Proxy logic disabled by request: always use direct connection, rely on system VPN ---
            # env_proxy_raw = os.getenv("TELEGRAM_PROXY_URL")
            # env_proxy_val = (str(env_proxy_raw).strip() if env_proxy_raw is not None else "")
            # # Treat TELEGRAM_PROXY_URL="" as "unset" so we can fall back to bot_config/system proxy.
            # if env_proxy_raw is not None and env_proxy_val:
            #     explicit_proxy_url = env_proxy_val
            #     explicit_proxy_source = "env"
            # else:
            #     explicit_proxy_url = (
            #         (bot_config.get("telegram_proxy_url") if isinstance(bot_config, dict) else None)
            #         or (bot_config.get("telegramProxyUrl") if isinstance(bot_config, dict) else None)
            #         or (bot_config.get("proxy_url") if isinstance(bot_config, dict) else None)
            #         or (bot_config.get("proxyUrl") if isinstance(bot_config, dict) else None)
            #     )
            #     if explicit_proxy_url:
            #         explicit_proxy_source = "bot_config"
            request_kwargs = dict(
                connection_pool_size=TELEGRAM_CONNECTION_POOL_SIZE,
                read_timeout=90,
                write_timeout=20,
                connect_timeout=20,
                pool_timeout=5,
                http_version="1.1",
                httpx_kwargs=httpx_kwargs,
            )
            request = HTTPXRequest(**request_kwargs)

            max_start_attempts = 3
            start_delay_seconds = 8
            last_err = None
            for attempt in range(1, max_start_attempts + 1):
                try:
                    builder = Application.builder().token(candidate.bot_token).request(request)
                    try:
                        if BOT_CONCURRENT_UPDATES > 1:
                            builder = builder.concurrent_updates(BOT_CONCURRENT_UPDATES)
                    except Exception:
                        pass
                    application = builder.build()
                    application.bot_data["candidate_id"] = candidate.id
                    application.add_handler(CommandHandler("start", start_command))
                    application.add_handler(CommandHandler("chatid", chatid_command))
                    application.add_handler(CommandHandler("myid", myid_command))
                    application.add_handler(MessageHandler((filters.TEXT | filters.CONTACT) & ~filters.COMMAND, handle_message))
                    application.add_handler(MessageHandler(filters.ALL, debug_update_logger), group=1)
                    application.add_error_handler(error_handler)

                    await application.initialize()
                    await application.start()
                    try:
                        await application.bot.delete_webhook(drop_pending_updates=False)
                    except Exception:
                        pass
                    await application.updater.start_polling(
                        drop_pending_updates=False,
                        timeout=poll_timeout,
                        read_timeout=poll_read_timeout,
                        connect_timeout=20,
                        write_timeout=20,
                        pool_timeout=5,
                        error_callback=polling_error_callback,
                    )
                    application.create_task(health_check_loop(application, candidate_id=candidate.id))
                    logger.info("Bot for %s is running.", candidate.full_name)
                    return application
                except (TimedOut, NetworkError) as e:
                    last_err = e
                    if attempt < max_start_attempts:
                        logger.warning(
                            "Bot start attempt %s/%s failed (%s). Retrying in %ss...",
                            attempt,
                            max_start_attempts,
                            type(e).__name__,
                            start_delay_seconds,
                        )
                        await asyncio.sleep(start_delay_seconds)
                    else:
                        raise

            if last_err is not None:
                raise last_err

        except Exception as e:
            logger.exception("Failed to start bot for %s (will auto-restart in 10s)", candidate.full_name)
            try:
                log_technical_error_sync(
                    service_name="telegram_bot",
                    error_type="StartFailed",
                    error_message=f"Failed to start polling for candidate_id={getattr(candidate, 'id', None)}: {e}",
                    telegram_user_id=None,
                    candidate_id=int(getattr(candidate, "id", 0) or 0) or None,
                    state=None,
                )
            except Exception:
                pass
            time.sleep(10)
            continue



async def stop_application(app: Application, *, candidate_id: int, reason: str) -> None:
    logger.info("Stopping bot for candidate_id=%s. reason=%s", candidate_id, reason)
    try:
        updater = getattr(app, "updater", None)
        if updater is not None and getattr(updater, "running", False):
            await updater.stop()
    except Exception as e:
        logger.warning("Failed stopping updater for candidate_id=%s: %s", candidate_id, e)

    try:
        if getattr(app, "running", False):
            await app.stop()
    except Exception as e:
        logger.warning("Failed stopping app for candidate_id=%s: %s", candidate_id, e)

    try:
        await app.shutdown()
    except Exception as e:
        logger.warning("Failed shutting down app for candidate_id=%s: %s", candidate_id, e)


async def check_for_new_candidates():
    while True:
        try:
            def get_active_candidates():
                db = SessionLocal()
                try:
                    return db.query(User).filter(User.role == "CANDIDATE", User.is_active == True).all()  # noqa: E712
                finally:
                    db.close()

            candidates = await run_db_query(get_active_candidates)
            active_ids: set[int] = set()

            for cid, app in list(running_bots.items()):
                try:
                    updater = getattr(app, "updater", None)
                    updater_running = bool(updater and getattr(updater, "running", False))
                    app_running = bool(getattr(app, "running", False))
                    if not updater_running or not app_running:
                        running_bots.pop(cid, None)
                        await stop_application(app, candidate_id=cid, reason="healthcheck: updater/app not running")
                        failed_bots[cid] = datetime.now(timezone.utc)
                except Exception as e:
                    logger.warning("Healthcheck failed for candidate_id=%s: %s", cid, e)

            for candidate in candidates:
                active_ids.add(int(candidate.id))
                if candidate.id not in running_bots:
                    last_failed_at = failed_bots.get(candidate.id)
                    if last_failed_at and (datetime.now(timezone.utc) - last_failed_at) < FAILED_BOT_COOLDOWN:
                        continue

                    if candidate.bot_token:
                        logger.info("Found new active candidate: %s. Starting bot...", candidate.full_name)
                        app = await run_bot(candidate)
                        if app:
                            running_bots[candidate.id] = app
                            failed_bots.pop(candidate.id, None)
                        else:
                            failed_bots[candidate.id] = datetime.now(timezone.utc)

            ids_to_stop = [cid for cid in running_bots.keys() if cid not in active_ids]
            for cid in ids_to_stop:
                app = running_bots.pop(cid, None)
                if app is None:
                    continue
                await stop_application(app, candidate_id=cid, reason="candidate deactivated")
                failed_bots.pop(cid, None)

        except Exception as e:
            logger.error("Error in candidate check loop: %s", e)

        await asyncio.sleep(10)


async def main() -> None:
    # Ensure DB tables exist
    Base.metadata.create_all(bind=engine)

    logger.info("Starting Bot Runner Service...")
    checker_task = asyncio.create_task(check_for_new_candidates())

    stop_signal = asyncio.Event()
    try:
        await stop_signal.wait()
    except KeyboardInterrupt:
        logger.info("Stopping bots...")
        stop_signal.set()
        checker_task.cancel()

        for app in running_bots.values():
            try:
                if app.updater.running:
                    await app.updater.stop()
            except Exception:
                pass
            try:
                if app.running:
                    await app.stop()
                    await app.shutdown()
            except Exception:
                pass
