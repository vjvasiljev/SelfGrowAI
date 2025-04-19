"""
Logging Utility for GrowAI

Configures application-wide logging to both file and console.
"""

import logging
import os

# Default log file path, can be overridden via environment variable
LOG_FILE = os.environ.get("GROWAI_LOG_PATH", "growai.log")


def setup_logging() -> logging.Logger:
    """
    Set up the 'growai' logger with a file handler and console handler.

    Returns:
        Configured logger instance.
    """
    logger = logging.getLogger("growai")
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers if called multiple times
    if logger.handlers:
        return logger

    # File handler
    fh = logging.FileHandler(LOG_FILE)
    fh.setLevel(logging.INFO)
    file_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    fh.setFormatter(file_formatter)
    logger.addHandler(fh)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    console_formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
    ch.setFormatter(console_formatter)
    logger.addHandler(ch)

    return logger
