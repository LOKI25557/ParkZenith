from fastapi import APIRouter

from .auth.router import router as auth_router
from .parking.router import router as parking_router
from .reservation.router import router as reservation_router
from .analytics.router import router as analytics_router
from .prediction.router import router as prediction_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(parking_router)
api_router.include_router(reservation_router)
api_router.include_router(analytics_router)
api_router.include_router(prediction_router)
