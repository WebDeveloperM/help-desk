"""Notification dependencies for dependency injection."""

from app.notification.dependencies.notification_deps import (
    get_notification_repository,
    get_notification_service,
)

__all__ = ["get_notification_repository", "get_notification_service"]
