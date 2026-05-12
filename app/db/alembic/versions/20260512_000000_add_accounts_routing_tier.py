"""add accounts routing tier

Revision ID: 20260512_000000_add_accounts_routing_tier
Revises: 20260507_000000_add_api_key_enforced_model_tiers
Create Date: 2026-05-12
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "20260512_000000_add_accounts_routing_tier"
down_revision = "20260507_000000_add_api_key_enforced_model_tiers"
branch_labels = None
depends_on = None


def _table_exists(connection: Connection, table_name: str) -> bool:
    inspector = sa.inspect(connection)
    return inspector.has_table(table_name)


def _columns(connection: Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(connection)
    if not inspector.has_table(table_name):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name) if column.get("name") is not None}


def upgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "accounts"):
        return

    existing_columns = _columns(bind, "accounts")
    with op.batch_alter_table("accounts") as batch_op:
        if "routing_tier" not in existing_columns:
            batch_op.add_column(sa.Column("routing_tier", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "accounts"):
        return

    existing_columns = _columns(bind, "accounts")
    with op.batch_alter_table("accounts") as batch_op:
        if "routing_tier" in existing_columns:
            batch_op.drop_column("routing_tier")
