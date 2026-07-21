"""
ParkZenith AI Service - Main FastAPI Application Entrypoint.
Phase 1: Data Collection Pipeline
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator, Dict, Any
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from ai_service.config.settings import settings
from ai_service.core.logging import setup_logging
from ai_service.core.exception_handlers import register_exception_handlers
from ai_service.database.session import init_db
from ai_service.scheduler.scheduler import collection_scheduler
from ai_service.api.routes import router as collector_router

# Initialize structured logging
setup_logging()
logger = logging.getLogger("ai_service.main")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application Lifespan Event Handler.
    Initializes database tables and starts background APScheduler on startup.
    Shuts down background scheduler gracefully on application exit.
    """
    logger.info("Initializing ParkZenith AI Service...")

    # Initialize database tables
    try:
        await init_db()
    except Exception as exc:
        logger.error("Failed to initialize database tables: %s", str(exc))

    # Start periodic collection background jobs
    collection_scheduler.start()

    logger.info("ParkZenith AI Service startup completed successfully.")

    yield

    # Shutdown background jobs
    logger.info("Shutting down ParkZenith AI Service...")
    collection_scheduler.shutdown()
    logger.info("ParkZenith AI Service shutdown finished.")


# Initialize FastAPI application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Data Collection & Preparation Pipeline for ParkZenith AI Analytics.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register custom exception handlers
register_exception_handlers(app)

# Include API Routers
app.include_router(collector_router)


@app.get("/health", tags=["Health Check"])
async def health_check() -> Dict[str, Any]:
    """
    Health check endpoint for AI Service monitoring.
    """
    return {
        "status": "UP",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT,
        "scheduler": collection_scheduler.status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ai_service.main:app", host="0.0.0.0", port=8001, reload=True)
