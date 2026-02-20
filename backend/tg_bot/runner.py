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

    # Otherwise auto-detect: if direct connection works, avoid env proxies.
    return {"trust_env": auto_decide_trust_env_for_telegram()}


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
                httpx_kwargs=_telegram_httpx_kwargs(),
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
                    await application.updater.start_polling(drop_pending_updates=False)
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
        #     else:
        #         explicit_proxy_url = windows_system_proxy_url()
        #         explicit_proxy_source = "windows_system" if explicit_proxy_url else "none"
        # explicit_proxy_url = (str(explicit_proxy_url).strip() if explicit_proxy_url is not None else "") or None
        # # If system proxy is 127.0.0.1:10808 but nothing listens there (e.g. VPN is app-only),
        # # using it causes ConnectError. Prefer direct connection with trust_env=False so
        # # system-wide VPN can carry the traffic.
        # skip_proxy_use_trust_env_false = False
        # if explicit_proxy_url and not env_truthy("TELEGRAM_ALLOW_LOCAL_PROXY"):
        #     try:
        #         parsed = urlparse(explicit_proxy_url)
        #         host = (parsed.hostname or "").lower()
        #         port = int(parsed.port) if parsed.port is not None else None
        #         if host in {"127.0.0.1", "localhost"} and port in {10808}:
        #             if auto_decide_trust_env_for_telegram():
        #                 logger.warning(
        #                     "Local proxy %s:%s is configured but direct connectivity failed earlier. "
        #                     "Using direct connection with trust_env=False so system VPN can be used; "
        #                     "if proxy is required, set TELEGRAM_ALLOW_LOCAL_PROXY=1 and ensure proxy is running.",
        #                     host,
        #                     port,
        #                 )
        #                 skip_proxy_use_trust_env_false = True
        #                 explicit_proxy_url = None
        #             else:
        #                 logger.warning(
        #                     "Ignoring TELEGRAM_PROXY_URL pointing to a local proxy (%s:%s). "
        #                     "Set TELEGRAM_ALLOW_LOCAL_PROXY=1 to force using it.",
        #                     host,
        #                     port,
        #                 )
        #                 explicit_proxy_url = None
        #     except Exception:
        #         pass

        request_kwargs = dict(
            connection_pool_size=TELEGRAM_CONNECTION_POOL_SIZE,
            read_timeout=90,
            write_timeout=20,
            connect_timeout=20,
            pool_timeout=5,
            httpx_kwargs=_telegram_httpx_kwargs(),
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
                await application.updater.start_polling(drop_pending_updates=False)
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
