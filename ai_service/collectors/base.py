"""
Abstract Base Collector class defining the standard collection lifecycle.
"""

from abc import ABC, abstractmethod
import logging
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from ai_service.schemas.collector import CollectionSummary
from ai_service.utils.backend_client import BackendAPIClient

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    """
    Abstract Base Collector for ingesting backend data into the AI Service database.
    """

    def __init__(self, backend_client: BackendAPIClient) -> None:
        self.backend_client = backend_client

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the collector."""
        pass

    @abstractmethod
    async def collect(self, session: AsyncSession) -> CollectionSummary:
        """
        Executes a complete collection cycle (fetch, validate, deduplicate, store).
        """
        pass
