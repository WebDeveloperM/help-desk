"""Pydantic schemas for ticket comments."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TicketCommentCreate(BaseModel):
    """Request body for creating a ticket comment."""

    body: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Comment text",
    )


class TicketCommentResponse(BaseModel):
    """Single ticket comment for API responses."""

    id: UUID
    ticket_id: UUID
    author_id: UUID
    author_full_name: str
    body: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TicketCommentListResponse(BaseModel):
    """Paginated list of ticket comments."""

    items: list[TicketCommentResponse]
    total: int
    page: int
    page_size: int
    pages: int
