"""
Base async repository class providing reusable CRUD, pagination, and bulk operations.
"""

from typing import Generic, TypeVar, Type, List, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, func, and_

from ai_service.database.base import Base
from ai_service.core.exceptions import DatabaseError

ModelType = TypeVar("ModelType", bound=Base)


class BaseAsyncRepository(Generic[ModelType]):
    """
    Abstract generic base repository for async SQLAlchemy 2.0.
    """

    def __init__(self, model: Type[ModelType], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def save(self, instance: ModelType) -> ModelType:
        """
        Saves a single model instance to the database.
        """
        try:
            self.session.add(instance)
            await self.session.flush()
            await self.session.refresh(instance)
            return instance
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to save {self.model.__name__} record: {str(exc)}",
                details={"model": self.model.__name__, "error": str(exc)},
            ) from exc

    async def save_many(self, instances: List[ModelType]) -> List[ModelType]:
        """
        Saves multiple model instances in a single bulk operation.
        """
        if not instances:
            return []
        try:
            self.session.add_all(instances)
            await self.session.flush()
            for inst in instances:
                await self.session.refresh(inst)
            return instances
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to bulk save {self.model.__name__} records: {str(exc)}",
                details={"model": self.model.__name__, "count": len(instances), "error": str(exc)},
            ) from exc

    async def get_all(
        self, limit: int = 100, offset: int = 0
    ) -> List[ModelType]:
        """
        Retrieves all records with limit and offset pagination.
        """
        try:
            stmt = select(self.model).limit(limit).offset(offset)
            result = await self.session.execute(stmt)
            return list(result.scalars().all())
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to retrieve {self.model.__name__} records: {str(exc)}",
                details={"model": self.model.__name__},
            ) from exc

    async def count(self) -> int:
        """
        Returns total count of records in the table.
        """
        try:
            stmt = select(func.count()).select_from(self.model)
            result = await self.session.execute(stmt)
            return result.scalar_one() or 0
        except Exception as exc:
            raise DatabaseError(
                message=f"Failed to count {self.model.__name__} records: {str(exc)}",
                details={"model": self.model.__name__},
            ) from exc
