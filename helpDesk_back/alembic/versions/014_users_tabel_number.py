"""users_tabel_number

Adds an optional personnel (tabel) number to `users`, surfaced/edited in the
admin Users page.

Revision ID: 014
Revises: 013
Create Date: 2026-07-09

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "014"
down_revision: Union[str, None] = "013"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "tabel_number",
            sa.String(length=50),
            nullable=True,
            comment="Personnel / employee (tabel) number",
        ),
    )
    op.create_index("ix_users_tabel_number", "users", ["tabel_number"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_tabel_number", table_name="users")
    op.drop_column("users", "tabel_number")
