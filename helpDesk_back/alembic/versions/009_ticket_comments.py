"""ticket_comments

Revision ID: 009
Revises: 008
Create Date: 2026-04-15

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "009"
down_revision: Union[str, None] = "008"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ticket_comments",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("author_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ticket_id"], ["tickets.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ticket_comments_ticket_id_created_at",
        "ticket_comments",
        ["ticket_id", "created_at"],
        unique=False,
    )
    op.create_index(
        "ix_ticket_comments_author_id",
        "ticket_comments",
        ["author_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_ticket_comments_author_id", table_name="ticket_comments")
    op.drop_index("ix_ticket_comments_ticket_id_created_at", table_name="ticket_comments")
    op.drop_table("ticket_comments")
