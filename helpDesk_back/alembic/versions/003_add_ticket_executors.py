"""add_ticket_executors

Revision ID: 003
Revises: 002
Create Date: 2026-01-29

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "003"
down_revision: Union[str, None] = "002a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_executors",
        sa.Column(
            "ticket_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("ticket_id", "user_id", name="pk_ticket_executors"),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            ondelete="CASCADE",
            name="fk_ticket_executors_ticket_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            ondelete="CASCADE",
            name="fk_ticket_executors_user_id",
        ),
    )
    op.create_index(
        "ix_ticket_executors_ticket_id",
        "ticket_executors",
        ["ticket_id"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_executors_user_id",
        "ticket_executors",
        ["user_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_executors_user_id", table_name="ticket_executors")
    op.drop_index("ix_ticket_executors_ticket_id", table_name="ticket_executors")
    op.drop_table("ticket_executors")
