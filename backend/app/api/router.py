from fastapi import APIRouter

from .auth.router import router as auth_router
from .users import router as users_router
from .facilities.router import router as facilities_router
from .zones.router import router as zones_router
from .slots.router import router as slots_router
from .reservation.router import router as reservation_router
from .analytics.router import router as analytics_router
from .prediction.router import router as prediction_router
from .heatmap.router import router as heatmap_router
from .payments.router import router as payments_router
from .sessions.router import router as sessions_router

api_router = APIRouter()

api_router.include_router(auth_router)
api_router.include_router(users_router)
api_router.include_router(facilities_router)
api_router.include_router(zones_router)
api_router.include_router(slots_router)
api_router.include_router(reservation_router)
api_router.include_router(analytics_router)
api_router.include_router(prediction_router)
api_router.include_router(heatmap_router)
api_router.include_router(payments_router)
api_router.include_router(sessions_router)

