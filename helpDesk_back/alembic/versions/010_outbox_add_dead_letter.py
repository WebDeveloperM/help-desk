"""outbox_add_dead_letter_status

Adds a terminal `dead_letter` value to the `outbox_status` enum so notification
outbox rows that have exhausted their retry budget can be marked separately
from transient failures (which still use `failed`).

Revision ID: 010
Revises: 009
Create Date: 2026-04-26

"""
from typing import Sequence, Union

from alembic import op

revision: str = "010"
down_revision: Union[str, None] = "009"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE outbox_status ADD VALUE IF NOT EXISTS 'dead_letter'")


def downgrade() -> None:
    # Postgres does not support removing a value from an enum type.
    # Downgrade is a no-op; remaining `dead_letter` rows stay valid.
    pass
