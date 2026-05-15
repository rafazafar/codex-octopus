"""add kiro account provider fields

Revision ID: 20260516_000000_add_kiro_account_provider_fields
Revises: 20260512_000000_add_accounts_routing_tier
Create Date: 2026-05-16 00:00:00.000000
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "20260516_000000_add_kiro_account_provider_fields"
down_revision = "20260512_000000_add_accounts_routing_tier"
branch_labels = None
depends_on = None

_ACCOUNT_PROVIDER_ENUM = sa.Enum("openai", "kiro", name="account_provider")


def _columns(bind: sa.engine.Connection, table_name: str) -> set[str]:
    inspector = sa.inspect(bind)
    if not inspector.has_table(table_name):
        return set()
    return {str(column["name"]) for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "accounts")
    with op.batch_alter_table("accounts") as batch_op:
        if "provider" not in columns:
            batch_op.add_column(
                sa.Column("provider", _ACCOUNT_PROVIDER_ENUM, nullable=False, server_default="openai")
            )
        if "kiro_auth_method" not in columns:
            batch_op.add_column(sa.Column("kiro_auth_method", sa.String(), nullable=True))
        if "kiro_client_id_encrypted" not in columns:
            batch_op.add_column(sa.Column("kiro_client_id_encrypted", sa.LargeBinary(), nullable=True))
        if "kiro_client_secret_encrypted" not in columns:
            batch_op.add_column(sa.Column("kiro_client_secret_encrypted", sa.LargeBinary(), nullable=True))
        if "kiro_region" not in columns:
            batch_op.add_column(sa.Column("kiro_region", sa.String(), nullable=True))
        if "kiro_expires_at" not in columns:
            batch_op.add_column(sa.Column("kiro_expires_at", sa.Integer(), nullable=True))
        if "kiro_machine_id" not in columns:
            batch_op.add_column(sa.Column("kiro_machine_id", sa.String(), nullable=True))
        if "kiro_profile_arn" not in columns:
            batch_op.add_column(sa.Column("kiro_profile_arn", sa.String(), nullable=True))
        if "kiro_provider" not in columns:
            batch_op.add_column(sa.Column("kiro_provider", sa.String(), nullable=True))
    op.execute(sa.text("UPDATE accounts SET provider = 'openai' WHERE provider IS NULL OR provider = ''"))


def downgrade() -> None:
    bind = op.get_bind()
    columns = _columns(bind, "accounts")
    with op.batch_alter_table("accounts") as batch_op:
        for column in (
            "kiro_provider",
            "kiro_profile_arn",
            "kiro_machine_id",
            "kiro_expires_at",
            "kiro_region",
            "kiro_client_secret_encrypted",
            "kiro_client_id_encrypted",
            "kiro_auth_method",
            "provider",
        ):
            if column in columns:
                batch_op.drop_column(column)
    # Drop the named enum type on PostgreSQL (no-op on SQLite)
    op.execute(sa.text("DROP TYPE IF EXISTS account_provider"))
