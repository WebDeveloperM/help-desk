"""local_auth

Adds local authentication columns to `users`, replacing the Keycloak-backed
identity. The backend now stores credentials and a single role directly:

- `username`      — unique login identifier.
- `password_hash` — bcrypt hash (nullable; e.g. legacy/imported rows).
- `role`          — single role (PG ENUM `role`, created in migration 002).

The `keycloak_id` column is kept as a stable internal subject id (now filled
with `str(user.id)` on create) to avoid churning FKs and indexes.

Revision ID: 013
Revises: 012
Create Date: 2026-06-30

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "013"
down_revision: Union[str, None] = "012"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "username",
            sa.String(length=100),
            nullable=True,
            comment="Login username",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=True,
            comment="Bcrypt password hash",
        ),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM(
                "user",
                "department_head",
                "executor",
                "admin",
                name="role",
                create_type=False,
            ),
            nullable=False,
            server_default="user",
            comment="User role",
        ),
    )

    # Backfill username for any pre-existing rows so the UNIQUE/NOT NULL hold.
    op.execute(
        "UPDATE users SET username = split_part(email, '@', 1) WHERE username IS NULL"
    )
    op.alter_column("users", "username", nullable=False)
    op.create_unique_constraint("uq_users_username", "users", ["username"])
    op.create_index("ix_users_username", "users", ["username"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_users_username", table_name="users")
    op.drop_constraint("uq_users_username", "users", type_="unique")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")
    op.drop_column("users", "username")
