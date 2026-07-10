"""add_notifications_and_outbox

Revision ID: 004
Revises: 003
Create Date: 2026-02-23

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create outbox_status enum for notification_outbox table
    op.execute("""
        CREATE TYPE outbox_status AS ENUM (
            'pending',
            'sent',
            'failed'
        )
    """)

    # Create notifications table
    op.create_table(
        "notifications",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("actor_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "notification_type",
            postgresql.ENUM(
                "ticket_created",
                "ticket_approved",
                "ticket_rejected",
                "ticket_assigned",
                "ticket_completed",
                "comment_added",
                "status_changed",
                name="notification_type",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("payload_json", postgresql.JSONB(), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("dedup_key", sa.String(length=512), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notifications"),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_notifications_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="CASCADE",
            name="fk_notifications_ticket_id",
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_notifications_actor_user_id",
        ),
        sa.UniqueConstraint("dedup_key", name="uq_notifications_dedup_key"),
    )
    op.create_index(
        "ix_notifications_user_id",
        "notifications",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_ticket_id",
        "notifications",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_notification_type",
        "notifications",
        ["notification_type"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_dedup_key",
        "notifications",
        ["dedup_key"],
        unique=True,
    )
    op.create_index(
        "ix_notifications_expires_at",
        "notifications",
        ["expires_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id_is_read_created_at",
        "notifications",
        ["user_id", "is_read", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_notifications_user_id_created_at",
        "notifications",
        ["user_id", "created_at"],
        unique=False,
    )

    # Create notification_outbox table
    op.create_table(
        "notification_outbox",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("routing_key", sa.String(length=255), nullable=False),
        sa.Column("payload_json", postgresql.JSONB(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "sent", "failed", name="outbox_status", create_type=False),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("next_retry_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name="pk_notification_outbox"),
    )
    op.create_index(
        "ix_notification_outbox_event_type",
        "notification_outbox",
        ["event_type"],
        unique=False,
    )
    op.create_index(
        "ix_notification_outbox_status",
        "notification_outbox",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_notification_outbox_status_next_retry_at",
        "notification_outbox",
        ["status", "next_retry_at"],
        unique=False,
    )
    op.create_index(
        "ix_notification_outbox_created_at",
        "notification_outbox",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_notification_outbox_created_at", table_name="notification_outbox")
    op.drop_index(
        "ix_notification_outbox_status_next_retry_at",
        table_name="notification_outbox",
    )
    op.drop_index("ix_notification_outbox_status", table_name="notification_outbox")
    op.drop_index("ix_notification_outbox_event_type", table_name="notification_outbox")
    op.drop_table("notification_outbox")

    op.drop_index("ix_notifications_user_id_created_at", table_name="notifications")
    op.drop_index(
        "ix_notifications_user_id_is_read_created_at",
        table_name="notifications",
    )
    op.drop_index("ix_notifications_expires_at", table_name="notifications")
    op.drop_index("ix_notifications_dedup_key", table_name="notifications")
    op.drop_index("ix_notifications_notification_type", table_name="notifications")
    op.drop_index("ix_notifications_ticket_id", table_name="notifications")
    op.drop_index("ix_notifications_user_id", table_name="notifications")
    op.drop_table("notifications")

    op.execute("DROP TYPE IF EXISTS outbox_status")
