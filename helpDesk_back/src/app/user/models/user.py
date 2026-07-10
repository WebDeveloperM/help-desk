"""User SQLAlchemy model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM as PG_ENUM
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import BaseModel
from app.core.enums import Role

if TYPE_CHECKING:
    from app.asset.models import Asset
    from app.department.models import Department
    from app.ticket.models import Ticket
    from app.ticket.models.ticket_comment import TicketComment
    from app.user.models.user_role import UserRole


class User(BaseModel):
    """User model representing a user in the system."""

    __tablename__ = "users"

    keycloak_id: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="Stable internal subject id (JWT sub); kept as keycloak_id for FK/index stability",
    )
    username: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        index=True,
        comment="Login username",
    )
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Bcrypt password hash",
    )
    tabel_number: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
        comment="Personnel / employee (tabel) number",
    )
    role: Mapped[Role] = mapped_column(
        PG_ENUM(
            Role,
            name="role",
            create_type=False,
            values_callable=lambda e: [member.value for member in e],
        ),
        nullable=False,
        default=Role.USER,
        server_default=Role.USER.value,
        comment="User role",
    )
    ad_username: Mapped[str | None] = mapped_column(
        String(100),
        unique=True,
        nullable=True,
        index=True,
        comment="Active Directory username (sAMAccountName)",
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        nullable=False,
        index=True,
        comment="User email address",
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="User full name",
    )
    full_name_uz: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User full name in Uzbek",
    )
    department_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="User department ID",
    )
    position: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User position",
    )
    position_uz: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User position in Uzbek",
    )
    phone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="User phone number",
    )
    ad_guid: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Active Directory GUID",
    )
    ad_distinguished_name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Active Directory Distinguished Name",
    )
    last_sync_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
        comment="Last synchronization time with Active Directory",
    )
    email_verified: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether email is verified in Keycloak",
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
        comment="Whether user is active (soft delete)",
    )

    # Relationships
    department: Mapped["Department | None"] = relationship(
        "Department",
        foreign_keys=[department_id],
        back_populates="users",
    )
    head_departments: Mapped[list["Department"]] = relationship(
        "Department",
        foreign_keys="Department.head_user_id",
        back_populates="head_user",
    )
    roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    created_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.created_by_id",
        back_populates="created_by",
    )
    approved_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.approver_user_id",
        back_populates="approver",
    )
    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.assigned_by_user_id",
        back_populates="assigned_by",
    )
    completed_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.completed_by_id",
        back_populates="completed_by",
    )
    closed_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        foreign_keys="Ticket.closed_by_id",
        back_populates="closed_by",
    )
    executor_tickets: Mapped[list["Ticket"]] = relationship(
        "Ticket",
        secondary="ticket_executors",
        back_populates="executors",
        lazy="selectin",
    )
    owned_assets: Mapped[list["Asset"]] = relationship(
        "Asset",
        foreign_keys="Asset.assigned_user_id",
        back_populates="assigned_user",
    )
    ticket_comments: Mapped[list["TicketComment"]] = relationship(
        "TicketComment",
        foreign_keys="TicketComment.author_id",
        back_populates="author",
    )

    __table_args__ = (
        UniqueConstraint("keycloak_id", name="uq_users_keycloak_id"),
        UniqueConstraint("username", name="uq_users_username"),
        UniqueConstraint("email", name="uq_users_email"),
        UniqueConstraint("ad_username", name="uq_users_ad_username"),
        Index("ix_users_keycloak_id", "keycloak_id"),
        Index("ix_users_username", "username"),
        Index("ix_users_email", "email"),
        Index("ix_users_ad_username", "ad_username"),
        Index("ix_users_department_id", "department_id"),
        Index("ix_users_is_active", "is_active"),
        Index("ix_users_ad_guid", "ad_guid"),
    )

    def __repr__(self) -> str:
        """String representation of user."""
        return f"<User(id={self.id}, email={self.email}, full_name={self.full_name})>"
