"""add_ticket_progress_percent

Revision ID: 005
Revises: 004
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "005"
down_revision: Union[str, None] = "004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "tickets",
        sa.Column(
            "progress_percent",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
    )
    op.create_index(
        "ix_tickets_progress_percent",
        "tickets",
        ["progress_percent"],
        unique=False,
    )
    op.alter_column("tickets", "progress_percent", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_tickets_progress_percent", table_name="tickets")
    op.drop_column("tickets", "progress_percent")
