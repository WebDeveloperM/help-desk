"""tickets and related tables (system_settings, ticket_categories, ticket_templates, tickets)

Revision ID: 002a
Revises: 002
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "002a"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # system_settings (referenced by generate_ticket_number in 002)
    op.create_table(
        "system_settings",
        sa.Column("key", sa.String(length=255), nullable=False),
        sa.Column("value", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("key", name="pk_system_settings"),
    )

    # ticket_categories (referenced by tickets)
    op.create_table(
        "ticket_categories",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ticket_categories"),
    )
    op.create_index("ix_ticket_categories_code", "ticket_categories", ["code"], unique=False)

    # ticket_templates (referenced by tickets)
    op.create_table(
        "ticket_templates",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_ticket_templates"),
    )

    # tickets
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "ticket_number",
            sa.String(length=50),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("created_by_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("creator_department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("category_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("template_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "pending_approval",
                "rejected",
                "approved",
                "assigned",
                "in_progress",
                "waiting_info",
                "completed",
                "closed",
                name="ticket_status",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column(
            "priority",
            postgresql.ENUM("low", "normal", "high", "urgent", name="ticket_priority", create_type=False),
            nullable=False,
        ),
        sa.Column("approver_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("approver_comment", sa.Text(), nullable=True),
        sa.Column("assigned_department_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_by_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("desired_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("planned_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actual_completion_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completion_comment", sa.Text(), nullable=True),
        sa.Column("closed_by_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_comment", sa.Text(), nullable=True),
        sa.Column("ticket_metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_urgent", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_tickets"),
        sa.ForeignKeyConstraint(["created_by_id"], ["users.id"], ondelete="RESTRICT", name="fk_tickets_created_by_id"),
        sa.ForeignKeyConstraint(
            ["creator_department_id"],
            ["departments.id"],
            ondelete="RESTRICT",
            name="fk_tickets_creator_department_id",
        ),
        sa.ForeignKeyConstraint(
            ["category_id"],
            ["ticket_categories.id"],
            ondelete="RESTRICT",
            name="fk_tickets_category_id",
        ),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["ticket_templates.id"],
            ondelete="SET NULL",
            name="fk_tickets_template_id",
        ),
        sa.ForeignKeyConstraint(
            ["approver_user_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_tickets_approver_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_department_id"],
            ["departments.id"],
            ondelete="SET NULL",
            name="fk_tickets_assigned_department_id",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_by_user_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_tickets_assigned_by_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["completed_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_tickets_completed_by_id",
        ),
        sa.ForeignKeyConstraint(
            ["closed_by_id"],
            ["users.id"],
            ondelete="SET NULL",
            name="fk_tickets_closed_by_id",
        ),
        sa.UniqueConstraint("ticket_number", name="uq_tickets_ticket_number"),
    )
    op.create_index("ix_tickets_ticket_number", "tickets", ["ticket_number"], unique=False)
    op.create_index("ix_tickets_status", "tickets", ["status"], unique=False)
    op.create_index("ix_tickets_created_by_id", "tickets", ["created_by_id"], unique=False)
    op.create_index("ix_tickets_category_id", "tickets", ["category_id"], unique=False)
    op.create_index("ix_tickets_assigned_dept_id", "tickets", ["assigned_department_id"], unique=False)
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"], unique=False)
    op.create_index("ix_tickets_status_created_at", "tickets", ["status", "created_at"], unique=False)
    op.create_index("ix_tickets_priority", "tickets", ["priority"], unique=False)
    op.create_index("ix_tickets_is_urgent", "tickets", ["is_urgent"], unique=False)

    # Trigger to auto-generate ticket_number on INSERT (uses generate_ticket_number() from 002)
    op.execute("""
        CREATE TRIGGER set_ticket_number
            BEFORE INSERT ON tickets
            FOR EACH ROW
            EXECUTE FUNCTION generate_ticket_number();
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS set_ticket_number ON tickets")
    op.drop_index("ix_tickets_is_urgent", table_name="tickets")
    op.drop_index("ix_tickets_priority", table_name="tickets")
    op.drop_index("ix_tickets_status_created_at", table_name="tickets")
    op.drop_index("ix_tickets_created_at", table_name="tickets")
    op.drop_index("ix_tickets_assigned_dept_id", table_name="tickets")
    op.drop_index("ix_tickets_category_id", table_name="tickets")
    op.drop_index("ix_tickets_created_by_id", table_name="tickets")
    op.drop_index("ix_tickets_status", table_name="tickets")
    op.drop_index("ix_tickets_ticket_number", table_name="tickets")
    op.drop_table("tickets")
    op.drop_index("ix_ticket_categories_code", table_name="ticket_categories")
    op.drop_table("ticket_templates")
    op.drop_table("ticket_categories")
    op.drop_table("system_settings")
