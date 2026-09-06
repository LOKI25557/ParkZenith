from fastapi import FastAPI, Response, status, Request
from fastapi.middleware.cors import CORSMiddleware
import httpx
import logging
import time
import uuid

from .core.config import settings
from .core.logging_setup import setup_logging, request_context
from .api.router import api_router
from .api.websocket.router import router as websocket_router
from .database.session import engine, AsyncSessionLocal

# Initialize structured logging formatter
setup_logging()
logger = logging.getLogger("backend.main")

app = FastAPI(title="ParkZenith API", debug=settings.DEBUG)

# Configure CORS origins dynamically
allowed_origins = [origin.strip() for origin in settings.ALLOWED_ORIGINS.split(",") if origin.strip()]
if settings.ENVIRONMENT == "production":
    if not allowed_origins or "*" in allowed_origins:
        # In production, default to empty to reject unauthorized requests unless configured
        logger.warning("Production environment detected. Wildcard CORS * is disabled for safety.")
        allowed_origins = []

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True if allowed_origins else False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
    response.headers["Content-Security-Policy"] = "default-src 'self';"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled Exception encountered at path=%s: %s", request.url.path, str(exc))
    
    if settings.ENVIRONMENT == "production":
        message = "An unexpected internal error occurred."
    else:
        message = str(exc)
        
    from fastapi.responses import JSONResponse
    request_id = request.headers.get("X-Request-ID", "unknown")
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "detail": message,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": message,
                "details": {"error_type": exc.__class__.__name__},
                "path": request.url.path,
                "request_id": request_id,
            }
        },
    )

from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import JSONResponse

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = request.headers.get("X-Request-ID", "unknown")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "detail": str(exc.detail),
            "error": {
                "code": f"HTTP_{exc.status_code}",
                "message": str(exc.detail),
                "details": None,
                "path": request.url.path,
                "request_id": request_id,
            }
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    request_id = request.headers.get("X-Request-ID", "unknown")
    errors = exc.errors()
    simplified_errors = [{"loc": err.get("loc"), "msg": err.get("msg"), "type": err.get("type")} for err in errors]
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "detail": "Validation Error",
            "error": {
                "code": "VALIDATION_ERROR",
                "message": "The request contains invalid data.",
                "details": simplified_errors,
                "path": request.url.path,
                "request_id": request_id,
            }
        },
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
        if settings.ENVIRONMENT == "production":
            message = "An unexpected internal error occurred."
        else:
            message = str(exc)
            
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "detail": message,
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": message,
                    "details": {"error_type": exc.__class__.__name__},
                    "path": request.url.path,
                }
            },
        )
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



# E2E & Data Sync API Endpoints
from datetime import datetime, timezone, timedelta
from typing import List, Optional
from pydantic import BaseModel
from fastapi import Depends
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from backend.app.database.session import get_async_session
from backend.app.models.parking_facility import ParkingFacility
from backend.app.models.parking_slot import ParkingSlot
from backend.app.models.reservation import Reservation, ReservationStatus
from backend.app.models.session import ParkingSession

class E2EReservationCreate(BaseModel):
    slot_id: int
    start_time: datetime
    end_time: datetime

# 1. Occupancy History Sync
@app.get("/occupancy/history")
@app.get("/api/v1/occupancy/history")
async def get_occupancy_history(limit: int = 500, db: AsyncSession = Depends(get_async_session)):
    stmt = select(ParkingFacility)
    facilities = (await db.execute(stmt)).scalars().all()
    history = []
    
    for f in facilities:
        from backend.app.models.parking_zone import ParkingZone
        from backend.app.models.parking_slot import ParkingSlotStatus
        total_stmt = select(func.count(ParkingSlot.id)).join(ParkingZone).where(ParkingZone.facility_id == f.id)
        occ_stmt = select(func.count(ParkingSlot.id)).join(ParkingZone).where(
            and_(ParkingZone.facility_id == f.id, ParkingSlot.status == ParkingSlotStatus.OCCUPIED)
        )
        total_slots = (await db.execute(total_stmt)).scalar() or 0
        occupied_slots = (await db.execute(occ_stmt)).scalar() or 0
        available_slots = total_slots - occupied_slots
        occ_pct = (occupied_slots / total_slots * 100.0) if total_slots > 0 else 0.0
        
        history.append({
            "facility_id": str(f.id),
            "zone_id": None,
            "total_slots": total_slots,
            "occupied_slots": occupied_slots,
            "available_slots": available_slots,
            "occupancy_percentage": round(occ_pct, 2),
            "collected_at": datetime.now(timezone.utc).isoformat()
        })
    return history

# 2. Reservation History Sync
@app.get("/reservations/history")
@app.get("/api/v1/reservations/history")
async def get_reservations_history(limit: int = 500, db: AsyncSession = Depends(get_async_session)):
    stmt = select(Reservation).limit(limit)
    reservations = (await db.execute(stmt)).scalars().all()
    history = []
    
    for r in reservations:
        duration = (r.end_time - r.start_time).total_seconds() / 60.0
        status_val = "COMPLETED"
        if r.status == ReservationStatus.CANCELLED:
            status_val = "CANCELLED"
        elif r.status == ReservationStatus.PENDING:
            status_val = "PENDING"
            
        history.append({
            "reservation_id": f"RES-{r.id}",
            "facility_id": "1", # default facility link for simplicity
            "slot_id": f"SLOT-{r.slot_id}",
            "reservation_status": status_val,
            "reservation_start": r.start_time.isoformat(),
            "reservation_end": r.end_time.isoformat(),
            "duration_minutes": round(duration, 2),
            "collected_at": r.created_at.isoformat() if r.created_at else datetime.now(timezone.utc).isoformat()
        })
    return history

# 3. Session History Sync
@app.get("/sessions/history")
@app.get("/api/v1/sessions/history")
async def get_sessions_history(limit: int = 500, db: AsyncSession = Depends(get_async_session)):
    stmt = select(ParkingSession).limit(limit)
    sessions = (await db.execute(stmt)).scalars().all()
    history = []
    
    for s in sessions:
        duration = 0.0
        if s.ended_at and s.started_at:
            duration = (s.ended_at - s.started_at).total_seconds() / 60.0
            
        history.append({
            "session_id": f"SESS-{s.id}",
            "facility_id": "1",
            "vehicle_type": "CAR",
            "check_in_time": s.started_at.isoformat(),
            "check_out_time": s.ended_at.isoformat() if s.ended_at else None,
            "duration_minutes": round(duration, 2),
            "parking_fee": round(s.fee, 2),
            "collected_at": s.started_at.isoformat()
        })
    return history




# Include API routers

app.include_router(api_router)
app.include_router(websocket_router)


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("backend.app.main:app", host="0.0.0.0", port=8000, reload=True)
