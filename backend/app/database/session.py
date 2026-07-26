from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

from ..core.config import settings

engine: AsyncEngine = create_async_engine(
    settings.DATABASE_URL, echo=settings.DEBUG, future=True
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_async_session() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
