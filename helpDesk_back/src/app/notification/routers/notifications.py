"""Notification router - list, mark read, mark all read."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from app.notification.dependencies import get_notification_service
from app.notification.schemas import (
    NotificationFilterParams,
    NotificationListResponse,
    NotificationResponse,
)
from app.notification.services import NotificationService
from app.user.dependencies import get_current_user_model
from app.user.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=NotificationListResponse)
async def list_notifications_endpoint(
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 100,
    is_read: Annotated[bool | None, Query()] = None,
) -> NotificationListResponse:
    """
    List notifications for the current user (paginated, optional is_read filter).

    Args:
        current_user: Current authenticated user.
        service: Notification service.
        page: Page number (1-indexed).
        page_size: Number of items per page.
        is_read: Filter by read status.

    Returns:
        Paginated notification list.
    """
    filters = NotificationFilterParams(is_read=is_read) if is_read is not None else None
    return await service.list_notifications(
        user_id=current_user.id,
        page=page,
        page_size=page_size,
        filters=filters,
    )


@router.post("/read-all")
async def mark_all_read_endpoint(
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> dict[str, int]:
    """
    Mark all notifications for the current user as read.

    Args:
        current_user: Current authenticated user.
        service: Notification service.

    Returns:
        Number of notifications marked as read.
    """
    count = await service.mark_all_read(current_user.id)
    return {"marked_count": count}


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read_endpoint(
    notification_id: UUID,
    current_user: Annotated[User, Depends(get_current_user_model)],
    service: Annotated[NotificationService, Depends(get_notification_service)],
) -> NotificationResponse:
    """
    Mark a single notification as read (only if it belongs to the current user).

    Args:
        notification_id: Notification UUID.
        current_user: Current authenticated user.
        service: Notification service.

    Returns:
        Updated notification.
    """
    return await service.mark_read(notification_id, current_user.id)
