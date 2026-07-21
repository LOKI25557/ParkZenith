"""
SQLAlchemy 2.0 DeclarativeBase model foundation.
"""

from datetime import datetime, timezone
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime


def current_utc_time() -> datetime:
    """Helper function to return timezone-aware UTC datetime."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models in AI Service.
    """

    pass
