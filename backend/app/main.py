from fastapi import FastAPI, Response, status, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
import time
import uuid

from .core.config import settings
from .core.logging_setup import setup_logging, request_context
from .api.router import api_router
from .database.session import engine, AsyncSessionLocal

# Initialize structured logging formatter
setup_logging()
logger = logging.getLogger("backend.main")

app = FastAPI(title="ParkZenith API", debug=settings.DEBUG)

# Configure CORS origins dynamically
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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
        
        # Record request metrics
        from .core.metrics import metrics
        metrics.record_request(request.url.path, response.status_code, duration_ms)

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
        
        # Record request failure metrics
        from .core.metrics import metrics
        metrics.record_request(request.url.path, 500, duration_ms)
        metrics.record_db_failure()  # Assume DB/Internal failure for exceptions

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


@app.on_event("startup")
async def startup_event():
    # place for startup tasks (migrations, connections, caches)
    pass


@app.on_event("shutdown")
async def shutdown_event():
    # cleanup tasks
    await engine.dispose()


@app.get("/", tags=["health"])
async def health_check():
    return {"message": "ParkZenith API Running"}


@app.get("/health", tags=["health"])
async def health():
    """Lightweight check to see if the API process is alive."""
    return {
        "status": "HEALTHY",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
    }


@app.get("/metrics", tags=["health"])
async def get_metrics():
    """Retrieve runtime application metrics."""
    from .core.metrics import metrics
    return metrics.get_metrics_summary()


@app.get("/ready", tags=["health"])
async def readiness_check(response: Response):
    """Verifies backend connectivity to database and the AI Service."""
    db_connected = False
    ai_service_connected = False

    # 1. Database Check
    try:
        from sqlalchemy import text
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        db_connected = True
    except Exception as exc:
        logger.error("Readiness check database connection failure: %s", str(exc))

    # 2. AI Service Check
    if not settings.AI_SERVICE_ENABLED:
        ai_service_connected = True
    else:
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{settings.AI_SERVICE_URL.rstrip('/')}/health")
                if res.status_code == 200:
                    ai_service_connected = True
                else:
                    logger.warning("AI Service health check returned HTTP %d", res.status_code)
        except Exception as exc:
            logger.error("Readiness check AI Service connection failure: %s", str(exc))

    if db_connected and ai_service_connected:
        status_str = "READY"
    elif db_connected or ai_service_connected:
        status_str = "DEGRADED"
    else:
        status_str = "NOT_READY"

    if status_str == "NOT_READY":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    elif status_str == "DEGRADED":
        response.status_code = status.HTTP_200_OK

    return {
        "status": status_str,
        "database": "CONNECTED" if db_connected else "DISCONNECTED",
        "ai_service": "CONNECTED" if ai_service_connected else "DISCONNECTED",
    }


# Include API routers
app.include_router(api_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
