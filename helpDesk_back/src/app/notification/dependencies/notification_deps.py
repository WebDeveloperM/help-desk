"""Notification dependencies for dependency injection."""

from typing import Annotated
from uuid import UUID

from fastapi import Depends

from app.core.database import DatabaseSession
from app.notification.repositories import (
    NotificationRepository,
    SQLAlchemyNotificationRepository,
)
from app.notification.services import NotificationService


def get_notification_repository(
    session: DatabaseSession,
) -> NotificationRepository:
    """
    Get notification repository instance.

    Args:
        session: Database session.

    Returns:
        Notification repository.
    """
    return SQLAlchemyNotificationRepository(session)


def get_notification_service(
    repository: Annotated[
        NotificationRepository,
        Depends(get_notification_repository),
    ],
) -> NotificationService:
    """
    Get notification service instance.

    Args:
        repository: Notification repository.

    Returns:
        Notification service.
    """
    return NotificationService(repository)
