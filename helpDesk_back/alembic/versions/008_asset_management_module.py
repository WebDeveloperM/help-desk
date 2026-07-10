"""asset_management_module

Revision ID: 008
Revises: 007
Create Date: 2026-03-16
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy import text
from sqlalchemy.dialects import postgresql

revision: str = "008"
down_revision: Union[str, None] = "007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

ASSET_STATUS_VALUES = ("active", "in_repair", "retired", "lost")
SEED_ASSETS = [
    ("HP LaserJet Pro M404", "printer", "PRN-0001", "HP-M404-0001"),
    ("Dell Latitude 5440", "laptop", "LTP-0001", "DLL-5440-0001"),
    ("Canon i-SENSYS MF264dw", "printer", "PRN-0002", "CNN-264-0001"),
]
ZERO_VECTOR = "[" + ",".join(["0"] * 16) + "]"


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    asset_status_enum = postgresql.ENUM(
        *ASSET_STATUS_VALUES,
        name="asset_lifecycle_status",
    )
    asset_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "assets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("asset_type", sa.String(length=100), nullable=False),
        sa.Column("inventory_number", sa.String(length=100), nullable=False),
        sa.Column("serial_number", sa.String(length=100), nullable=True),
        sa.Column("department_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assigned_user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                *ASSET_STATUS_VALUES,
                name="asset_lifecycle_status",
                create_type=False,
            ),
            nullable=False,
            server_default=sa.text("'active'"),
        ),
        sa.Column("location", sa.String(length=255), nullable=True),
        sa.Column("purchase_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("warranty_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column(
            "image_urls",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("embedding", Vector(16), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
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
        sa.ForeignKeyConstraint(
            ["department_id"],
            ["departments.id"],
            name="fk_assets_department_id",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["assigned_user_id"],
            ["users.id"],
            name="fk_assets_assigned_user_id",
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_assets"),
        sa.UniqueConstraint("inventory_number", name="uq_assets_inventory_number"),
    )

    op.create_index("ix_assets_asset_type", "assets", ["asset_type"], unique=False)
    op.create_index("ix_assets_department_id", "assets", ["department_id"], unique=False)
    op.create_index("ix_assets_assigned_user_id", "assets", ["assigned_user_id"], unique=False)
    op.create_index("ix_assets_status", "assets", ["status"], unique=False)
    op.create_index("ix_assets_name", "assets", ["name"], unique=False)
    op.create_index("ix_assets_is_active", "assets", ["is_active"], unique=False)
    op.create_index(
        "ix_assets_embedding_hnsw",
        "assets",
        [sa.text("embedding")],
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )

    op.create_table(
        "ticket_assets",
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("asset_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["ticket_id"],
            ["tickets.id"],
            name="fk_ticket_assets_ticket_id",
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["asset_id"],
            ["assets.id"],
            name="fk_ticket_assets_asset_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("ticket_id", "asset_id", name="pk_ticket_assets"),
    )
    op.create_index("ix_ticket_assets_asset_id", "ticket_assets", ["asset_id"], unique=False)

    conn = op.get_bind()
    for name, asset_type, inventory_number, serial_number in SEED_ASSETS:
        conn.execute(
            text(
                """
                INSERT INTO assets (
                    id,
                    name,
                    asset_type,
                    inventory_number,
                    serial_number,
                    department_id,
                    assigned_user_id,
                    status,
                    image_urls,
                    embedding,
                    is_active
                )
                SELECT
                    gen_random_uuid(),
                    :name,
                    :asset_type,
                    :inventory_number,
                    :serial_number,
                    d.id,
                    (
                        SELECT u.id
                        FROM users u
                        WHERE u.department_id = d.id
                        ORDER BY u.created_at
                        LIMIT 1
                    ),
                    'active',
                    '[]'::jsonb,
                    CAST(:embedding AS vector),
                    true
                FROM departments d
                WHERE NOT EXISTS (
                    SELECT 1 FROM assets a WHERE a.inventory_number = :inventory_number_check
                )
                ORDER BY d.created_at
                LIMIT 1
                """
            ),
            {
                "name": name,
                "asset_type": asset_type,
                "inventory_number": inventory_number,
                # Separate bind for NOT EXISTS: asyncpg errors if the same name is reused
                # with incompatible inferred types (text vs varchar).
                "inventory_number_check": inventory_number,
                "serial_number": serial_number,
                "embedding": ZERO_VECTOR,
            },
        )


def downgrade() -> None:
    op.drop_index("ix_ticket_assets_asset_id", table_name="ticket_assets")
    op.drop_table("ticket_assets")

    op.drop_index("ix_assets_embedding_hnsw", table_name="assets")
    op.drop_index("ix_assets_is_active", table_name="assets")
    op.drop_index("ix_assets_name", table_name="assets")
    op.drop_index("ix_assets_status", table_name="assets")
    op.drop_index("ix_assets_assigned_user_id", table_name="assets")
    op.drop_index("ix_assets_department_id", table_name="assets")
    op.drop_index("ix_assets_asset_type", table_name="assets")
    op.drop_table("assets")

    asset_status_enum = postgresql.ENUM(
        *ASSET_STATUS_VALUES,
        name="asset_lifecycle_status",
    )
    asset_status_enum.drop(op.get_bind(), checkfirst=True)
