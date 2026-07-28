"""
FastAPI exception handlers for custom AI service exceptions and general errors.
"""

import logging
from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse

from ai_service.core.exceptions import AIServiceBaseException

logger = logging.getLogger("ai_service.exception_handler")


def register_exception_handlers(app: FastAPI) -> None:
    """
    Registers custom exception handlers on the provided FastAPI application instance.
    """

    @app.exception_handler(AIServiceBaseException)
    async def ai_service_exception_handler(
        request: Request, exc: AIServiceBaseException
    ) -> JSONResponse:
        logger.error(
            "Custom Exception Triggered: %s (code=%s, status=%d, path=%s)",
            exc.message,
            exc.error_code,
            exc.status_code,
            request.url.path,
            extra={"details": exc.details},
        )
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": exc.error_code,
                    "message": exc.message,
                    "details": exc.details,
                    "path": request.url.path,
                }
            },
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.exception(
            "Unhandled Exception encountered at path=%s: %s",
            request.url.path,
            str(exc),
        )
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected internal error occurred.",
                    "details": {"error_type": exc.__class__.__name__},
                    "path": request.url.path,
                }
            },
        )
