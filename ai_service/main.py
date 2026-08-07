"""
ParkZenith AI Service - Main FastAPI Application Entrypoint.
Phase 1: Data Collection Pipeline
"""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator, Dict, Any
from fastapi import FastAPI, Response, status, Request
from fastapi.middleware.cors import CORSMiddleware
import time
import uuid

from ai_service.config.settings import settings
from ai_service.core.logging import setup_logging, request_context
from ai_service.core.exception_handlers import register_exception_handlers
from ai_service.database.session import init_db
from ai_service.scheduler.scheduler import collection_scheduler
from ai_service.api.routes import router as collector_router
from ai_service.api.analytics_routes import router as analytics_router
from ai_service.api.preprocessing_routes import router as preprocessing_router
from ai_service.api.forecasting_routes import router as forecasting_router
from ai_service.api.availability_routes import router as availability_router
from ai_service.api.recommendation_routes import router as recommendation_router
from ai_service.api.queue_routes import router as queue_router
from ai_service.api.intelligence_routes import router as intelligence_router
from ai_service.api.heatmap_routes import router as heatmap_router
from ai_service.api.event_routes import router as event_router



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


@app.middleware("http")
async def log_requests(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    ctx = {
        "request_id": request_id,
        "method": request.method,
        "route": request.url.path,
        "client_ip": request.client.host if request.client else "unknown",
    }
    
    # Extract facility ID if present in query params or path
    if "facility_id" in request.path_params:
        ctx["facility_id"] = str(request.path_params["facility_id"])
    elif "facility_id" in request.query_params:
        ctx["facility_id"] = str(request.query_params["facility_id"])

    token = request_context.set(ctx)
    start_time = time.time()
    logger.info("Request started: %s %s", request.method, request.url.path)
    
    try:
        response = await call_next(request)
        duration_ms = int((time.time() - start_time) * 1000)
        logger.info(
            "Request completed: %s %s | status=%d | duration=%dms",
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
            extra={
                "status_code": response.status_code,
                "duration_ms": duration_ms
            }
        )
        response.headers["X-Request-ID"] = request_id
        return response
    except Exception as exc:
        duration_ms = int((time.time() - start_time) * 1000)
        logger.exception(
            "Request failed: %s %s | error=%s | duration=%dms",
            request.method,
            request.url.path,
            str(exc),
            duration_ms,
            extra={
                "status_code": 500,
                "duration_ms": duration_ms
            }
        )
        raise exc
    finally:
        request_context.reset(token)


# Register custom exception handlers
register_exception_handlers(app)

# Include API Routers
app.include_router(collector_router)
app.include_router(analytics_router)
app.include_router(preprocessing_router)
app.include_router(forecasting_router)
app.include_router(availability_router)
app.include_router(recommendation_router)
app.include_router(queue_router)
app.include_router(intelligence_router)
app.include_router(heatmap_router)
app.include_router(event_router)




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


@app.get("/ready", tags=["Health Check"])
async def readiness_check(response: Response) -> Dict[str, Any]:
    """
    Readiness check endpoint. Verifies database connectivity and ML model loading.
    """
    db_connected = False
    models_ready = False

    # 1. Database Check
    try:
        from sqlalchemy import text
        from ai_service.database.session import AsyncSessionFactory
        async with AsyncSessionFactory() as session:
            await session.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        logger.error("Readiness probe database connection failure: %s", str(exc))

    # 2. Model Availability Check
    try:
        from ai_service.api.deps import get_forecasting_service
        forecasting = get_forecasting_service()
        models_ready = forecasting.forecaster.is_loaded
    except Exception as exc:
        logger.error("Readiness probe model check failure: %s", str(exc))

    status_str = "READY" if (db_connected and models_ready) else "DEGRADED"

    # If not ready, return 503 Service Unavailable
    if status_str != "READY":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": status_str,
        "database_connected": db_connected,
        "models_ready": models_ready,
        "scheduler_status": collection_scheduler.status,
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("ai_service.main:app", host="0.0.0.0", port=8001, reload=True)
