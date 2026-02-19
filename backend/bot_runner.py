import asyncio
import os

from tg_bot.bootstrap import setup_logging
from tg_bot.lock import acquire_single_instance_lock, default_lock_path
from tg_bot.runner import main as runner_main


def _lock_path() -> str:
    return (os.getenv("BOT_RUNNER_LOCK_PATH") or "").strip() or default_lock_path()


def main() -> None:
    setup_logging()
    acquire_single_instance_lock(_lock_path())
    import logging
    import time
    while True:
        try:
            asyncio.run(runner_main())
        except KeyboardInterrupt:
            logging.info("Bot stopped by user (KeyboardInterrupt). Exiting...")
            break
        except BaseException as e:
            logging.exception("Bot crashed (BaseException), will restart in 30 seconds: %s", e)
            time.sleep(30)


if __name__ == "__main__":
    main()
