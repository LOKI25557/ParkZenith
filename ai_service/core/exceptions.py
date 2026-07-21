"""
Custom exceptions for ParkZenith AI Data Collection Service.
"""

from typing import Any, Dict, Optional


class AIServiceBaseException(Exception):
    """
    Base exception class for all custom AI Service errors.
    """

    def __init__(
        self,
        message: str,
        status_code: int = 500,
        error_code: str = "INTERNAL_SERVER_ERROR",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code
        self.details = details or {}


class BackendUnavailableError(AIServiceBaseException):
    """
    Raised when the main ParkZenith backend API is unreachable or returns 5xx status codes.
    """

    def __init__(
        self,
        message: str = "Backend service is currently unavailable.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=503,
            error_code="BACKEND_UNAVAILABLE",
            details=details,
        )


class CollectionError(AIServiceBaseException):
    """
    Raised when a data collector fails to parse, validate, or process data.
    """

    def __init__(
        self,
        message: str = "An error occurred during data collection.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="COLLECTION_FAILED",
            details=details,
        )


class DuplicateDataError(AIServiceBaseException):
    """
    Raised when duplicate data items are encountered during ingestion where strict uniqueness is required.
    """

    def __init__(
        self,
        message: str = "Duplicate record detected.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=409,
            error_code="DUPLICATE_DATA",
            details=details,
        )


class DatabaseError(AIServiceBaseException):
    """
    Raised when a database interaction fails.
    """

    def __init__(
        self,
        message: str = "Database operation failed.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=500,
            error_code="DATABASE_ERROR",
            details=details,
        )
