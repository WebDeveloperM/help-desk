"""Ticket SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    Index,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM, JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel
from app.core.enums import TicketPriority, TicketStatus

if TYPE_CHECKING:
    from app.asset.models import Asset
    from app.department.models import Department
    from app.ticket.models.ticket_comment import TicketComment
    from app.user.models import User

# Association table for ticket executors (many-to-many Ticket <-> User)
ticket_executors_table = Table(
    "ticket_executors",
    BaseModel.metadata,
    Column(
        "ticket_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "user_id",
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)

# Association table for ticket assets (many-to-many Ticket <-> Asset)
ticket_assets_table = Table(
    "ticket_assets",
    BaseModel.metadata,
    Column(
        "ticket_id",
        PG_UUID(as_uuid=True),
        ForeignKey("tickets.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "asset_id",
        PG_UUID(as_uuid=True),
        ForeignKey("assets.id", ondelete="CASCADE"),
        primary_key=True,
        nullable=False,
    ),
    Column(
        "created_at",
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    ),
)


class Ticket(BaseModel):
    """Ticket model representing a help desk ticket."""

    __tablename__ = "tickets"

    ticket_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        index=True,
        comment="Unique ticket number (generated automatically)",
    )

    # Creator information
    created_by_id: Mapped[UUID] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="User who created the ticket",
    )
    creator_department_id: Mapped[UUID] = mapped_column(
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=False,
        comment="Department of the ticket creator",
    )

    # Category and template
    category_id: Mapped[UUID] = mapped_column(
        ForeignKey("ticket_categories.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        comment="Ticket category",
    )
    template_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("ticket_templates.id", ondelete="SET NULL"),
        nullable=True,
        comment="Ticket template used",
    )

    # Ticket content
    title: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="Ticket title",
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Ticket description",
    )

    # Status and priority
    status: Mapped[TicketStatus] = mapped_column(
        PG_ENUM(
            TicketStatus,
            name="ticket_status",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=TicketStatus.DRAFT,
        index=True,
        comment="Ticket status",
    )
    priority: Mapped[TicketPriority] = mapped_column(
        PG_ENUM(
            TicketPriority,
            name="ticket_priority",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=TicketPriority.NORMAL,
        index=True,
        comment="Ticket priority",
    )

    # Approval information
    approver_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who approved the ticket",
    )
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Approval timestamp",
    )
    approver_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Approver comment",
    )

    # Assignment information
    assigned_department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Department assigned to handle the ticket",
    )
    assigned_by_user_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who assigned the ticket",
    )
    assigned_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Assignment timestamp",
    )

    # Completion dates
    desired_completion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Desired completion date",
    )
    planned_completion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Planned completion date",
    )
    actual_completion_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Actual completion date",
    )

    # Completion information
    completed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who completed the ticket",
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Completion timestamp",
    )
    completion_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Completion comment",
    )

    # Closure information
    closed_by_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who closed the ticket",
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Closure timestamp",
    )
    closed_comment: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Closure comment",
    )

    # Additional fields
    ticket_metadata: Mapped[dict | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="JSON with additional category-specific data",
    )
    is_urgent: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
        comment="Urgent flag",
    )
    progress_percent: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        default=0,
        comment="Implementation progress percentage [0..100]",
    )

    # Relationships
    created_by: Mapped["User"] = relationship(
        "User",
        foreign_keys=[created_by_id],
        back_populates="created_tickets",
    )
    creator_department: Mapped["Department"] = relationship(
        "Department",
        foreign_keys=[creator_department_id],
        back_populates="created_tickets",
    )
    approver: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[approver_user_id],
        back_populates="approved_tickets",
    )
    assigned_department: Mapped["Department | None"] = relationship(
        "Department",
        foreign_keys=[assigned_department_id],
        back_populates="assigned_tickets",
    )
    assigned_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[assigned_by_user_id],
        back_populates="assigned_tickets",
    )
    completed_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[completed_by_id],
        back_populates="completed_tickets",
    )
    closed_by: Mapped["User | None"] = relationship(
        "User",
        foreign_keys=[closed_by_id],
        back_populates="closed_tickets",
    )
    executors: Mapped[list["User"]] = relationship(
        "User",
        secondary=ticket_executors_table,
        back_populates="executor_tickets",
        lazy="selectin",
    )
    assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        secondary=ticket_assets_table,
        back_populates="tickets",
        lazy="selectin",
    )
    comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment",
        back_populates="ticket",
    )

    __table_args__ = (
        UniqueConstraint("ticket_number", name="uq_tickets_ticket_number"),
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_created_by_id", "created_by_id"),
        Index("ix_tickets_category_id", "category_id"),
        Index("ix_tickets_assigned_dept_id", "assigned_department_id"),
        Index("ix_tickets_created_at", "created_at"),
        Index("ix_tickets_status_created_at", "status", "created_at"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_is_urgent", "is_urgent"),
        Index("ix_tickets_progress_percent", "progress_percent"),
    )

    def __repr__(self) -> str:
        """String representation of ticket."""
        return (
            f"<Ticket(id={self.id}, ticket_number={self.ticket_number}, "
            f"status={self.status.value}, priority={self.priority.value})>"
        )
