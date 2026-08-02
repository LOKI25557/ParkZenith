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


class EmptyDatasetError(AIServiceBaseException):
    """
    Raised when an analytics request has no historical records available.
    """

    def __init__(
        self,
        message: str = "No data found matching the specified parameters.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code="EMPTY_DATASET",
            details=details,
        )


class MissingFacilityError(AIServiceBaseException):
    """
    Raised when a specified facility ID does not exist or has never been tracked.
    """

    def __init__(
        self,
        message: str = "The specified facility was not found.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code="MISSING_FACILITY",
            details=details,
        )


class InvalidDateRangeError(AIServiceBaseException):
    """
    Raised when the provided date query parameters are invalid (e.g. end date before start date).
    """

    def __init__(
        self,
        message: str = "Invalid date range parameters.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="INVALID_DATE_RANGE",
            details=details,
        )


class ModelUnavailableError(AIServiceBaseException):
    """
    Raised when an ML model is not trained, missing, corrupted, or incompatible.
    """

    def __init__(
        self,
        message: str = "Forecasting model is currently unavailable or not trained.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=404,
            error_code="MODEL_UNAVAILABLE",
            details=details,
        )


class InsufficientDataError(AIServiceBaseException):
    """
    Raised when there is not enough historical data/logs to train models or calculate predictions.
    """

    def __init__(
        self,
        message: str = "Insufficient historical data available for operation.",
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            message=message,
            status_code=400,
            error_code="INSUFFICIENT_DATA",
            details=details,
        )


