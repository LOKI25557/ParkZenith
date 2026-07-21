"""
Structured logging module for ParkZenith AI Service.
"""

import sys
import logging
from ai_service.config.settings import settings


class StructuredLogFormatter(logging.Formatter):
    """
    Custom log formatter providing clean, consistent structured output.
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, "%Y-%m-%dT%H:%M:%S%z")
        log_message = super().format(record)
        details = getattr(record, "details", None)
        if details:
            log_message = f"{log_message} | details={details}"
        return f"[{timestamp}] [{record.levelname:<7}] [{record.name}] {log_message}"


def setup_logging() -> None:
    """
    Initializes global application logging settings.
    """
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    # Console Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)
    console_handler.setFormatter(
        StructuredLogFormatter(
            fmt="%(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S",
        )
    )

    root_logger.addHandler(console_handler)

    # Disable verbose logging from third party libraries
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.INFO)
