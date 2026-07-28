"""
Async database session management using SQLAlchemy 2.0.
"""

from typing import AsyncGenerator
import logging
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncEngine,
    async_sessionmaker,
    create_async_engine,
)

from ai_service.config.settings import settings
from ai_service.database.base import Base

logger = logging.getLogger(__name__)

# Create async engine with connection pooling settings
engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DB_ECHO,
    future=True,
)

# Async session factory
AsyncSessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


async def init_db() -> None:
    """
    Creates all database tables defined in models if they do not exist.
    """
    logger.info("Initializing database tables for URL: %s", settings.DATABASE_URL)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized successfully.")


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency generator for providing async database sessions to FastAPI routes or services.
    """
    async with AsyncSessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
