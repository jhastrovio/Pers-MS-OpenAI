import logging
from typing import Optional

_configured = False

def configure_logging(level: int = logging.DEBUG, filename: str = "app.log") -> None:
    """Configure the root logger once.

    Subsequent calls have no effect.

    Args:
        level: Logging level to use for the root logger.
        filename: File to write logs to.
    """
    global _configured
    if _configured:
        return

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(filename)],
    )
    _configured = True

def get_logger(name):
    """Get a logger instance with the specified name.

    Args:
        name: The name of the logger.

    Returns:
        A logger instance.
    """
    configure_logging()
    return logging.getLogger(name)
