"""Database infrastructure for async SQLAlchemy."""

from datetime import datetime
from typing import Annotated, AsyncGenerator
from uuid import UUID, uuid4

from fastapi import Depends
from sqlalchemy import DateTime, String, func
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import Settings, get_settings


class Base(DeclarativeBase):
    """Base model class with common fields."""

    pass


class TimestampMixin:
    """Mixin for timestamp fields."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class BaseModel(Base, TimestampMixin):
    """Base model with ID and timestamps."""

    __abstract__ = True

    id: Mapped[UUID] = mapped_column(
        primary_key=True,
        default=uuid4,
        nullable=False,
    )


# Global engine and session factory
_engine = None
_session_factory = None


def init_database(settings: Settings) -> None:
    """
    Initialize database engine and session factory.

    Args:
        settings: Application settings.
    """
    global _engine, _session_factory

    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=settings.debug,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
        )

        _session_factory = async_sessionmaker(
            _engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """
    Return the async session factory (must be called after init_database).

    Returns:
        Session factory for creating new sessions.

    Raises:
        RuntimeError: If database has not been initialized.
    """
    global _session_factory
    if _session_factory is None:
        raise RuntimeError("Database not initialized; call init_database first")
    return _session_factory


async def close_database() -> None:
    """Close database connections."""
    global _engine

    if _engine:
        await _engine.dispose()


async def get_db_session(
    settings: Settings = Depends(get_settings),
) -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.

    Args:
        settings: Application settings.

    Yields:
        Async database session.
    """
    global _session_factory

    if _session_factory is None:
        init_database(settings)

    async with _session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# Type alias for dependency injection
DatabaseSession = Annotated[AsyncSession, Depends(get_db_session)]
