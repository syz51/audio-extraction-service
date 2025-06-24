"""
Logging utilities and configuration.
"""

import logging
import sys
from typing import Any, Dict

from app.core.config import settings


def setup_logging() -> None:
    """Configure application logging without interfering with FastAPI/Uvicorn loggers."""
    log_level = getattr(logging, settings.log_level.upper(), logging.INFO)

    # Get our application's root logger
    app_logger = logging.getLogger("app")

    # Only configure if not already configured
    if not app_logger.handlers:
        # Create formatter
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )

        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(log_level)

        # Configure our app logger
        app_logger.setLevel(log_level)
        app_logger.addHandler(console_handler)
        # Prevent propagation to root logger to avoid duplicates
        app_logger.propagate = False


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name under the app namespace."""
    # Ensure all our loggers are under the 'app' namespace
    if not name.startswith("app."):
        name = f"app.{name}"
    return logging.getLogger(name)


def log_event_processing(
    event_type: str, record_count: int, additional_info: Dict[str, Any] | None = None
) -> None:
    """Log event processing information in a structured way."""
    logger = get_logger("event_processor")

    log_data = {
        "event_type": event_type,
        "record_count": record_count,
    }

    if additional_info:
        log_data.update(additional_info)

    logger.info(f"Event processing: {log_data}")
