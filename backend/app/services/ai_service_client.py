"""
Asynchronous HTTP Client for backend integration with ParkZenith AI Service.
Supports occupancy prediction, availability checks, smart recommendations,
analytics queries, and virtual queue operations.
"""

import logging
from typing import Dict, Any, Optional
import httpx

from backend.app.core.config import settings

logger = logging.getLogger("backend.services.ai_client")


class AIServiceClient:
    """
    HTTP Client wrapper for AI Service APIs with structured logging,
    timeouts, and robust error handling.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.AI_SERVICE_URL).rstrip("/")
        self.timeout = timeout or settings.AI_SERVICE_TIMEOUT

    async def _make_request(
        self,
        method: str,
        path: str,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Executes HTTP request, catches network errors, and wraps them in a consistent structure.
        """
        if not settings.AI_SERVICE_ENABLED:
            logger.warning("AI Service is disabled in settings. Request to %s skipped.", path)
            return {
                "success": False,
                "error": {
                    "code": "AI_SERVICE_DISABLED",
                    "message": "AI Service integration is disabled in configuration.",
                },
            }

        url = f"{self.base_url}{path}"
        logger.info("Executing AI Service request: %s %s", method, url)

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    json=json_data,
                )

                if response.status_code >= 400:
                    try:
                        err_data = response.json()
                        err_payload = err_data.get("error", {})
                        err_msg = err_payload.get("message") or response.text
                        err_code = err_payload.get("code") or "AI_SERVICE_ERROR"
                    except Exception:
                        err_msg = response.text
                        err_code = "AI_SERVICE_ERROR"

                    logger.error(
                        "AI Service error response (HTTP %d) on path %s: %s",
                        response.status_code,
                        path,
                        err_msg,
                    )
                    return {
                        "success": False,
                        "error": {
                            "code": err_code,
                            "message": err_msg,
                            "status_code": response.status_code,
                        },
                    }

                data = response.json()
                return {"success": True, "data": data}

        except httpx.TimeoutException as exc:
            logger.error("Timeout connecting to AI Service at %s: %s", url, str(exc))
            return {
                "success": False,
                "error": {
                    "code": "AI_SERVICE_TIMEOUT",
                    "message": "The connection to the AI Service timed out.",
                },
            }
        except (httpx.ConnectError, httpx.RequestError) as exc:
            logger.error("Connection failure connecting to AI Service at %s: %s", url, str(exc))
            return {
                "success": False,
                "error": {
                    "code": "AI_SERVICE_UNAVAILABLE",
                    "message": "The AI Service is currently unreachable or down.",
                },
            }
        except Exception as exc:
            logger.exception("Unexpected error in AI Service client for path %s: %s", path, str(exc))
            return {
                "success": False,
                "error": {
                    "code": "AI_SERVICE_INTERNAL_ERROR",
                    "message": "An unexpected error occurred during service-to-service communication.",
                },
            }

    # --- Occupancy Predictions ---
    async def get_occupancy_prediction(
        self, facility_id: int, horizon_minutes: int
    ) -> Dict[str, Any]:
        """
        Retrieves occupancy forecasts (15, 30, 60 or custom horizons).
        """
        if horizon_minutes in (15, 30, 60):
            return await self._make_request(
                "GET",
                f"/forecast/{horizon_minutes}",
                params={"facility_id": facility_id},
            )
        else:
            return await self._make_request(
                "POST",
                "/forecast/custom",
                json_data={"facility_id": facility_id, "target_minutes": horizon_minutes},
            )

    # --- Availability Predictions ---
    async def get_availability_prediction(
        self, facility_id: str, eta_minutes: int = 20
    ) -> Dict[str, Any]:
        """
        Retrieves availability probability prediction for a facility.
        """
        return await self._make_request(
            "GET",
            f"/availability/{facility_id}",
            params={"eta_minutes": eta_minutes},
        )

    # --- Smart Recommendations ---
    async def get_recommendations(
        self,
        latitude: float,
        longitude: float,
        eta_minutes: int = 20,
        destination_latitude: Optional[float] = None,
        destination_longitude: Optional[float] = None,
        max_distance_km: float = 5.0,
        max_results: int = 5,
        max_parking_fee: Optional[float] = None,
        parking_type: Optional[str] = None,
        preferred_facility: Optional[str] = None,
        accessibility_required: bool = False,
        weights: Optional[Dict[str, float]] = None,
    ) -> Dict[str, Any]:
        """
        Fetches ranked parking recommendations from Smart Recommendation Engine.
        """
        payload = {
            "latitude": latitude,
            "longitude": longitude,
            "eta_minutes": eta_minutes,
            "destination_latitude": destination_latitude,
            "destination_longitude": destination_longitude,
            "max_distance_km": max_distance_km,
            "max_results": max_results,
            "max_parking_fee": max_parking_fee,
            "parking_type": parking_type,
            "preferred_facility": preferred_facility,
            "accessibility_required": accessibility_required,
        }
        if weights:
            payload["weights"] = weights

        return await self._make_request("POST", "/recommendations", json_data=payload)

    # --- Analytics Engine Queries ---
    async def get_analytics_overview(
        self,
        facility_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Fetches high-level summary overview of analytics metrics.
        """
        params = {}
        if facility_id:
            params["facility_id"] = facility_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._make_request("GET", "/analytics/overview", params=params)

    async def get_daily_report(
        self,
        facility_id: Optional[str] = None,
        date_str: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compiles structured daily report.
        """
        params = {}
        if facility_id:
            params["facility_id"] = facility_id
        if date_str:
            params["date"] = date_str
        return await self._make_request("GET", "/analytics/daily", params=params)

    async def get_weekly_report(
        self,
        facility_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Compiles structured weekly report.
        """
        params = {}
        if facility_id:
            params["facility_id"] = facility_id
        if start_date:
            params["start_date"] = start_date
        if end_date:
            params["end_date"] = end_date
        return await self._make_request("GET", "/analytics/weekly", params=params)

    # --- Virtual Queue operations ---
    async def get_queue_status(self, facility_id: str) -> Dict[str, Any]:
        """
        Gets current queue statistics estimation.
        """
        return await self._make_request("GET", f"/queue/{facility_id}")

    async def get_queue_prediction(
        self, facility_id: str, eta_minutes: int = 20
    ) -> Dict[str, Any]:
        """
        Gets predicted queue statistics at eta_minutes.
        """
        return await self._make_request(
            "GET",
            f"/queue/{facility_id}/prediction",
            params={"eta_minutes": eta_minutes},
        )

    async def enqueue_driver(self, facility_id: str, user_id: str) -> Dict[str, Any]:
        """
        Enqueues a user in the facility virtual queue.
        """
        return await self._make_request(
            "POST",
            f"/queue/{facility_id}/enqueue",
            json_data={"user_id": user_id},
        )

    async def dequeue_driver(
        self, facility_id: str, user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Dequeues a driver (or next driver if user_id is None).
        """
        payload = {}
        if user_id:
            payload["user_id"] = user_id
        return await self._make_request(
            "POST",
            f"/queue/{facility_id}/dequeue",
            json_data=payload,
        )

    async def get_queue_position(self, facility_id: str, user_id: str) -> Dict[str, Any]:
        """
        Looks up a user's position in the virtual queue.
        """
        return await self._make_request(
            "GET",
            f"/queue/{facility_id}/position",
            params={"user_id": user_id},
        )

    async def cancel_queue_position(self, facility_id: str, user_id: str) -> Dict[str, Any]:
        """
        Cancels a user's spot in the queue.
        """
        return await self._make_request(
            "POST",
            f"/queue/{facility_id}/cancel",
            json_data={"user_id": user_id},
        )


# Singleton client instance
ai_service_client = AIServiceClient()
