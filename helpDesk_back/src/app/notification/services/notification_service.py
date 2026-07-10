"""Notification service - business logic for notification operations."""

from math import ceil
from uuid import UUID

from app.notification.exceptions import (
    NotificationNotFoundError,
    NotificationPermissionDeniedError,
)
from app.notification.repositories import NotificationRepository
from app.notification.schemas import (
    NotificationFilterParams,
    NotificationListResponse,
    NotificationResponse,
)


class NotificationService:
    """Service for notification business logic operations."""

    def __init__(self, repository: NotificationRepository) -> None:
        """
        Initialize notification service.

        Args:
            repository: Notification repository for database operations.
        """
        self.repository = repository

    async def list_notifications(
        self,
        user_id: UUID,
        page: int = 1,
        page_size: int = 100,
        filters: NotificationFilterParams | None = None,
    ) -> NotificationListResponse:
        """
        List notifications for the current user with pagination.

        Args:
            user_id: Current user UUID.
            page: Page number (1-indexed).
            page_size: Number of items per page.
            filters: Optional filter parameters (e.g. is_read).

        Returns:
            Paginated notification list response.
        """
        skip = (page - 1) * page_size
        is_read = filters.is_read if filters else None
        notifications, total = await self.repository.list_by_user_id(
            user_id=user_id,
            skip=skip,
            limit=page_size,
            is_read=is_read,
        )
        pages = ceil(total / page_size) if total > 0 else 0
        return NotificationListResponse(
            items=[NotificationResponse.model_validate(n) for n in notifications],
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )

    async def mark_read(
        self, notification_id: UUID, user_id: UUID
    ) -> NotificationResponse:
        """
        Mark a notification as read (only for the owning user).

        Args:
            notification_id: Notification UUID.
            user_id: Current user UUID (must own the notification).

        Returns:
            Updated notification.

        Raises:
            NotificationNotFoundError: If notification not found.
            NotificationPermissionDeniedError: If user doesn't own the notification.
        """
        notification = await self.repository.get_by_id(notification_id)
        if not notification:
            raise NotificationNotFoundError(notification_id=str(notification_id))
        if notification.user_id != user_id:
            raise NotificationPermissionDeniedError()
        updated = await self.repository.mark_read(notification_id, user_id)
        if not updated:
            raise NotificationNotFoundError(notification_id=str(notification_id))
        return NotificationResponse.model_validate(updated)

    async def mark_all_read(self, user_id: UUID) -> int:
        """
        Mark all notifications for the user as read.

        Args:
            user_id: Current user UUID.

        Returns:
            Number of notifications marked as read.
        """
        return await self.repository.mark_all_read(user_id)

    async def get_unread_count(self, user_id: UUID) -> int:
        """
        Get unread notification count for the user (excluding expired).

        Args:
            user_id: Current user UUID.

        Returns:
            Unread count.
        """
        return await self.repository.count_unread(user_id)
