"""
API package initialization.
"""

from ai_service.api.routes import router
from ai_service.api.analytics_routes import router as analytics_router

__all__ = ["router", "analytics_router"]

