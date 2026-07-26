"""Logging configuration for the reminder system."""

from __future__ import annotations

import logging
from pathlib import Path


LOGGER_NAME = "activity_reminder"


def setup_logging(log_dir: Path) -> logging.Logger:
    """Configure application logging and return the application logger."""

    log_dir.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    if logger.handlers:
        return logger

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    from logging.handlers import RotatingFileHandler
    
    email_handler = RotatingFileHandler(log_dir / "email.log", encoding="utf-8", maxBytes=5 * 1024 * 1024, backupCount=5)
    email_handler.setLevel(logging.INFO)
    email_handler.setFormatter(formatter)

    error_handler = RotatingFileHandler(log_dir / "error.log", encoding="utf-8", maxBytes=5 * 1024 * 1024, backupCount=5)
    error_handler.setLevel(logging.WARNING)
    error_handler.setFormatter(formatter)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    logger.addHandler(email_handler)
    logger.addHandler(error_handler)
    logger.addHandler(console_handler)

    return logger

