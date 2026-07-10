"""System dependencies for dependency injection."""

from typing import Annotated

from fastapi import Depends

from app.core.database import DatabaseSession
from app.system.repositories import SQLAlchemySystemRepository, SystemRepository
from app.system.services import SystemService


def get_system_repository(session: DatabaseSession) -> SystemRepository:
    """
    Get system repository instance.

    Args:
        session: Database session.

    Returns:
        System repository.
    """
    return SQLAlchemySystemRepository(session)


def get_system_service(
    repository: Annotated[SystemRepository, Depends(get_system_repository)],
) -> SystemService:
    """
    Get system service instance.

    Args:
        repository: System repository.

    Returns:
        System service.
    """
    return SystemService(repository)
