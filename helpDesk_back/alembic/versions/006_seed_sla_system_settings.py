"""seed_sla_system_settings

Revision ID: 006
Revises: 005
Create Date: 2026-03-05

"""
from typing import Sequence, Union

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = "006"
down_revision: Union[str, None] = "005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_SLA_SETTINGS = [
    ("sla.low.hours", "72"),
    ("sla.normal.hours", "48"),
    ("sla.high.hours", "24"),
    ("sla.urgent.hours", "8"),
]


def upgrade() -> None:
    conn = op.get_bind()
    for key, value in DEFAULT_SLA_SETTINGS:
        conn.execute(
            text(
                "INSERT INTO system_settings (key, value) VALUES (:key, :value) ON CONFLICT (key) DO NOTHING"
            ),
            {"key": key, "value": value},
        )


def downgrade() -> None:
    conn = op.get_bind()
    for key, _ in DEFAULT_SLA_SETTINGS:
        conn.execute(text("DELETE FROM system_settings WHERE key = :key"), {"key": key})
