"""add api key enforced model tiers

Revision ID: 20260507_000000_add_api_key_enforced_model_tiers
Revises: 20260419_020000_add_automation_run_cycles_snapshot_tables
Create Date: 2026-05-07
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Connection

revision = "20260507_000000_add_api_key_enforced_model_tiers"
down_revision = "20260419_020000_add_automation_run_cycles_snapshot_tables"
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
    if not _table_exists(bind, "api_keys"):
        return

    existing_columns = _columns(bind, "api_keys")
    with op.batch_alter_table("api_keys") as batch_op:
        if "enforced_model_tiers" not in existing_columns:
            batch_op.add_column(sa.Column("enforced_model_tiers", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    if not _table_exists(bind, "api_keys"):
        return

    existing_columns = _columns(bind, "api_keys")
    with op.batch_alter_table("api_keys") as batch_op:
        if "enforced_model_tiers" in existing_columns:
            batch_op.drop_column("enforced_model_tiers")
