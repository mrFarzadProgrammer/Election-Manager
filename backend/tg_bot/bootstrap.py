import logging

from .monitoring import install_409_conflict_logger


def setup_logging() -> None:
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
        force=True,
    )

    # Avoid leaking Telegram bot token via HTTP request logs (URLs contain /bot<token>/...)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    install_409_conflict_logger()
