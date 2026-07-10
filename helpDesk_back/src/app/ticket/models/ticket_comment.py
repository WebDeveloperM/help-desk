"""Ticket comment SQLAlchemy model."""

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, Index, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel

if TYPE_CHECKING:
    from app.ticket.models.ticket import Ticket
    from app.user.models import User


class TicketComment(BaseModel):
    """User comment on a ticket (discussion thread)."""

    __tablename__ = "ticket_comments"

    ticket_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Ticket this comment belongs to",
    )
    author_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who wrote the comment",
    )
    body: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Comment text",
    )

    ticket: Mapped["Ticket"] = relationship(
        "Ticket",
        back_populates="comments",
    )
    author: Mapped["User"] = relationship(
        "User",
        foreign_keys=[author_id],
        back_populates="ticket_comments",
    )

    __table_args__ = (
        Index(
            "ix_ticket_comments_ticket_id_created_at",
            "ticket_id",
            "created_at",
        ),
    )
