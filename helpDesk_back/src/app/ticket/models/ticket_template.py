"""Ticket template model (referenced by tickets.template_id)."""

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import BaseModel


class TicketTemplate(BaseModel):
    """Ticket template model (referenced by Ticket.template_id)."""

    __tablename__ = "ticket_templates"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
