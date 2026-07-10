"""Notification domain exceptions with HTTP mapping."""

from fastapi import status

from app.core.exceptions import DomainError


class NotificationNotFoundError(DomainError):
    """Raised when notification is not found."""

    def __init__(
        self, notification_id: str | None = None, detail: str | None = None
    ) -> None:
        message = detail or (
            f"Notification with id {notification_id} not found"
            if notification_id
            else "Notification not found"
        )
        params = {"notification_id": notification_id} if notification_id else {}
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            error_code="notification.not_found",
            detail=message,
            error_params=params,
        )


class NotificationPermissionDeniedError(DomainError):
    """Raised when user doesn't have permission to access the notification."""

    def __init__(
        self, detail: str = "You don't have permission to access this notification"
    ) -> None:
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            error_code="notification.permission_denied",
            detail=detail,
        )
