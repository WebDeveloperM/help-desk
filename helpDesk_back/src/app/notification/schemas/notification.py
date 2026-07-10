"""Notification Pydantic schemas for request/response validation."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.enums import NotificationType


class NotificationResponse(BaseModel):
    """Schema for notification response."""

    id: UUID
    user_id: UUID
    ticket_id: UUID | None = None
    actor_user_id: UUID | None = None
    notification_type: NotificationType
    title: str
    body: str | None = None
    payload_json: dict[str, Any] | None = None
    is_read: bool
    read_at: datetime | None = None
    expires_at: datetime
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class NotificationListResponse(BaseModel):
    """Schema for paginated notification list response."""

    items: list[NotificationResponse]
    total: int
    page: int
    page_size: int
    pages: int


class NotificationFilterParams(BaseModel):
    """Schema for notification filtering parameters."""

    is_read: bool | None = None
