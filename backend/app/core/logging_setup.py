import json
import logging
import sys
from datetime import datetime, timezone
from contextvars import ContextVar
from typing import Any, Dict

from backend.app.core.config import settings

# ContextVar to store request-specific context like request_id
request_context: ContextVar[Dict[str, Any]] = ContextVar("request_context", default={})


class ProductionJSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": settings.PROJECT_NAME,
            "environment": settings.ENVIRONMENT,
        }

        # Inject context variables (e.g. request_id, route, method)
        ctx = request_context.get()
        if ctx:
            log_data.update(ctx)

        # Handle details dict if passed
        details = getattr(record, "details", None)
        if details and isinstance(details, dict):
            for k, v in details.items():
                if any(secret in k.lower() for secret in ("password", "token", "secret", "key", "credential", "database")):
                    log_data[k] = "[REDACTED]"
                else:
                    log_data[k] = v

        # Redact messages that might contain sensitive parameters
        msg = log_data["message"]
        for secret_word in ("password=", "token=", "secret=", "key=", "credential="):
            if secret_word in msg.lower():
                log_data["message"] = "[REDACTED SENSITIVE INFO]"

        return json.dumps(log_data)


class DevelopmentFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")
        ctx = request_context.get()
        req_id_str = f" [req_id={ctx['request_id']}]" if ctx and "request_id" in ctx else ""
        log_message = super().format(record)
        return f"[{timestamp}] [{record.levelname:<7}] [{record.name}]{req_id_str} {log_message}"


def setup_logging() -> None:
    log_level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)
    root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    if settings.ENVIRONMENT == "production":
        console_handler.setFormatter(ProductionJSONFormatter())
    else:
        console_handler.setFormatter(DevelopmentFormatter("%(message)s"))

    root_logger.addHandler(console_handler)

    # Disable double logging issues from third party libs
    logging.getLogger("uvicorn.access").propagate = False
    logging.getLogger("uvicorn.error").propagate = False
