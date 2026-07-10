"""Notification repositories."""

from app.notification.repositories.interfaces import NotificationRepository
from app.notification.repositories.notification_repo import SQLAlchemyNotificationRepository

__all__ = ["NotificationRepository", "SQLAlchemyNotificationRepository"]
