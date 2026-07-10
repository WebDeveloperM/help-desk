"""Ticket category model for listing categories."""

from uuid import UUID

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import BaseModel


class TicketCategory(BaseModel):
    """Ticket category model (read-only for listing)."""

    __tablename__ = "ticket_categories"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str | None] = mapped_column(String(50), nullable=True)
