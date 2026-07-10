"""Ticket comment repository."""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from app.ticket.models import TicketComment


class SQLAlchemyTicketCommentRepository:
    """Repository for ticket comment persistence."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        ticket_id: UUID,
        author_id: UUID,
        body: str,
    ) -> TicketComment:
        comment = TicketComment(
            ticket_id=ticket_id,
            author_id=author_id,
            body=body,
        )
        self.session.add(comment)
        await self.session.flush()
        stmt = (
            select(TicketComment)
            .where(TicketComment.id == comment.id)
            .options(joinedload(TicketComment.author))
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_by_ticket(
        self,
        ticket_id: UUID,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> tuple[list[TicketComment], int]:
        count_stmt = (
            select(func.count())
            .select_from(TicketComment)
            .where(TicketComment.ticket_id == ticket_id)
        )
        total = int((await self.session.execute(count_stmt)).scalar_one())

        stmt = (
            select(TicketComment)
            .where(TicketComment.ticket_id == ticket_id)
            .options(joinedload(TicketComment.author))
            .order_by(TicketComment.created_at.asc())
            .offset(skip)
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        items = list(result.scalars().unique().all())
        return items, total
