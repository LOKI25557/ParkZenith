"""
HTTP Client for communicating asynchronously with the main ParkZenith Backend API.
Uses httpx with configurable retries, timeouts, and error handling.
"""

import asyncio
import logging
from typing import List, Dict, Any, Type, TypeVar, Optional
import httpx
from pydantic import BaseModel, ValidationError

from ai_service.config.settings import settings
from ai_service.core.exceptions import BackendUnavailableError, CollectionError
from ai_service.schemas.occupancy import OccupancyHistoryCreate
from ai_service.schemas.reservation import ReservationHistoryCreate
from ai_service.schemas.session import ParkingSessionHistoryCreate

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class BackendAPIClient:
    """
    Asynchronous HTTP client for fetching historical data endpoints from the main backend.
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_backoff: Optional[float] = None,
    ) -> None:
        self.base_url = (base_url or settings.BACKEND_API_URL).rstrip("/")
        self.timeout = timeout or settings.HTTP_TIMEOUT_SECONDS
        self.max_retries = max_retries or settings.HTTP_MAX_RETRIES
        self.retry_backoff = retry_backoff or settings.HTTP_RETRY_BACKOFF_FACTOR

    def _get_headers(self) -> Dict[str, str]:
        headers = {"Accept": "application/json", "User-Agent": "ParkZenith-AIService/1.0"}
        if settings.BACKEND_API_KEY:
            headers["X-API-Key"] = settings.BACKEND_API_KEY
        return headers

    async def _make_request_with_retry(
        self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None
    ) -> Any:
        """
        Executes an HTTP request with exponential backoff retries.
        """
        url = f"{self.base_url}{endpoint}"
        last_exception: Optional[Exception] = None

        for attempt in range(1, self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    logger.debug(
                        "Sending %s request to %s (Attempt %d/%d)",
                        method,
                        url,
                        attempt,
                        self.max_retries,
                    )
                    response = await client.request(
                        method=method,
                        url=url,
                        headers=self._get_headers(),
                        params=params,
                    )

                    if response.status_code >= 500:
                        raise httpx.HTTPStatusError(
                            f"Server Error {response.status_code}",
                            request=response.request,
                            response=response,
                        )

                    response.raise_for_status()
                    return response.json()

            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.ReadTimeout) as exc:
                last_exception = exc
                logger.warning(
                    "Network error connecting to backend %s on attempt %d/%d: %s",
                    url,
                    attempt,
                    self.max_retries,
                    str(exc),
                )
            except httpx.HTTPStatusError as exc:
                last_exception = exc
                if exc.response.status_code < 500:
                    # Client errors (4xx) should not retry
                    logger.error(
                        "Client HTTP error %d from %s: %s",
                        exc.response.status_code,
                        url,
                        exc.response.text,
                    )
                    raise BackendUnavailableError(
                        message=f"Backend API returned HTTP {exc.response.status_code} for {endpoint}",
                        details={"status_code": exc.response.status_code, "url": url},
                    ) from exc
                logger.warning(
                    "Backend server error HTTP %d from %s on attempt %d/%d",
                    exc.response.status_code,
                    url,
                    attempt,
                    self.max_retries,
                )

            if attempt < self.max_retries:
                sleep_time = self.retry_backoff * (2 ** (attempt - 1))
                await asyncio.sleep(sleep_time)

        # If all retries failed
        raise BackendUnavailableError(
            message=f"Backend API at {url} is unavailable after {self.max_retries} attempts.",
            details={"endpoint": endpoint, "error": str(last_exception)},
        ) from last_exception

    def _parse_pydantic_list(
        self, raw_data: Any, schema_cls: Type[T]
    ) -> List[T]:
        """
        Parses raw list of dicts into validated Pydantic schema objects.
        """
        if not isinstance(raw_data, list):
            # If backend wraps items in a dict e.g. {"items": [...]} or {"data": [...]}
            if isinstance(raw_data, dict):
                raw_data = raw_data.get("items") or raw_data.get("data") or []
            else:
                raw_data = []

        parsed_items: List[T] = []
        for index, item in enumerate(raw_data):
            try:
                parsed_items.append(schema_cls.model_validate(item))
            except ValidationError as exc:
                logger.error(
                    "Failed to validate %s at index %d: %s",
                    schema_cls.__name__,
                    index,
                    str(exc),
                )

        return parsed_items

    async def fetch_occupancy_history(
        self, limit: int = 500
    ) -> List[OccupancyHistoryCreate]:
        """
        Fetches historical occupancy data from GET /occupancy/history.
        """
        raw_json = await self._make_request_with_retry("GET", "/occupancy/history", params={"limit": limit})
        return self._parse_pydantic_list(raw_json, OccupancyHistoryCreate)

    async def fetch_reservations_history(
        self, limit: int = 500
    ) -> List[ReservationHistoryCreate]:
        """
        Fetches historical reservation data from GET /reservations/history.
        """
        raw_json = await self._make_request_with_retry("GET", "/reservations/history", params={"limit": limit})
        return self._parse_pydantic_list(raw_json, ReservationHistoryCreate)

    async def fetch_sessions_history(
        self, limit: int = 500
    ) -> List[ParkingSessionHistoryCreate]:
        """
        Fetches historical parking session data from GET /sessions/history.
        """
        raw_json = await self._make_request_with_retry("GET", "/sessions/history", params={"limit": limit})
        return self._parse_pydantic_list(raw_json, ParkingSessionHistoryCreate)
