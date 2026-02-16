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
    asyncio.run(runner_main())


if __name__ == "__main__":
    main()
