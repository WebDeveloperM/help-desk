"""Service for ticket discussion comments."""

from __future__ import annotations

from math import ceil
from uuid import UUID

from app.notification.repositories import NotificationRepository
from app.notification.services.ticket_notifications import (
    create_notifications_for_comment_added,
)
from app.ticket.exceptions import TicketValidationError
from app.ticket.models import Ticket, TicketComment
from app.ticket.repositories.interfaces import TicketCommentRepository
from app.ticket.schemas.ticket_comment import (
    TicketCommentListResponse,
    TicketCommentResponse,
)
from app.user.models import User


def _comment_to_response(comment: TicketComment) -> TicketCommentResponse:
    author = comment.author
    return TicketCommentResponse(
        id=comment.id,
        ticket_id=comment.ticket_id,
        author_id=comment.author_id,
        author_full_name=author.full_name if author else "",
        body=comment.body,
        created_at=comment.created_at,
    )


class TicketCommentService:
    """Create and list ticket comments."""

    def __init__(
        self,
        comment_repository: TicketCommentRepository,
        notification_repository: NotificationRepository,
    ) -> None:
        self._comment_repository = comment_repository
        self._notification_repository = notification_repository

    async def create_comment(
        self,
        ticket: Ticket,
        author: User,
        body: str,
    ) -> TicketCommentResponse:
        text = body.strip()
        if not text:
            raise TicketValidationError(detail="Comment body cannot be empty")

        comment = await self._comment_repository.create(
            ticket_id=ticket.id,
            author_id=author.id,
            body=text,
        )
        await create_notifications_for_comment_added(
            self._notification_repository,
            ticket,
            actor_user_id=author.id,
            comment_id=comment.id,
            actor_full_name=author.full_name,
        )
        return _comment_to_response(comment)

    async def list_comments(
        self,
        ticket_id: UUID,
        *,
        page: int = 1,
        page_size: int = 100,
    ) -> TicketCommentListResponse:
        skip = (page - 1) * page_size
        rows, total = await self._comment_repository.list_by_ticket(
            ticket_id,
            skip=skip,
            limit=page_size,
        )
        pages = ceil(total / page_size) if total > 0 else 0
        items = [_comment_to_response(c) for c in rows]
        return TicketCommentListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            pages=pages,
        )
