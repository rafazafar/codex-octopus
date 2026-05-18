"""add request log provider fields

Revision ID: 20260516_010000_add_request_log_provider_fields
Revises: 20260516_000000_add_kiro_account_provider_fields
Create Date: 2026-05-16 01:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260516_010000_add_request_log_provider_fields"
down_revision = "20260516_000000_add_kiro_account_provider_fields"
branch_labels = None
depends_on = None


def _columns(bind: sa.engine.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "request_logs")
    with op.batch_alter_table("request_logs") as batch_op:
        if "provider" not in columns:
            batch_op.add_column(sa.Column("provider", sa.String(), nullable=True))
        if "upstream_model" not in columns:
            batch_op.add_column(sa.Column("upstream_model", sa.String(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "request_logs")
    with op.batch_alter_table("request_logs") as batch_op:
        for column in ("upstream_model", "provider"):
            if column in columns:
                batch_op.drop_column(column)
