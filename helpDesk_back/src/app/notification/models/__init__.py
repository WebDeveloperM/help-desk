"""Notification models."""

from app.notification.models.notification import Notification
from app.notification.models.outbox import NotificationOutbox

__all__ = ["Notification", "NotificationOutbox"]
