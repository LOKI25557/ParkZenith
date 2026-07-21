"""
Core module initialization.
"""

from ai_service.core.exceptions import (
    AIServiceBaseException,
    BackendUnavailableError,
    CollectionError,
    DuplicateDataError,
    DatabaseError,
)
from ai_service.core.logging import setup_logging

__all__ = [
    "AIServiceBaseException",
    "BackendUnavailableError",
    "CollectionError",
    "DuplicateDataError",
    "DatabaseError",
    "setup_logging",
]
