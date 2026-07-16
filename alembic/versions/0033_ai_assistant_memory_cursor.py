"""ai assistant memory extraction cursor

Revision ID: 0033_ai_assistant_memory_cursor
Revises: 0032_ai_assistant_memory_scope
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0033_ai_assistant_memory_cursor"
down_revision: str | None = "0032_ai_assistant_memory_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "ai_assistant_memory_cursor" not in tables:
        _create_cursor()
    if "ai_assistant_memory_completion" not in tables:
        _create_completion_ledger()
    op.execute(
        sa.text(
            "INSERT IGNORE INTO ai_assistant_memory_completion "
            "(user_id, workspace_id, run_id, completed_at, created_at, updated_at) "
            "SELECT user_id, workspace_id, id, completed_at, NOW(), NOW() "
            "FROM ai_assistant_run WHERE status = 'COMPLETED' AND completed_at IS NOT NULL "
            "ORDER BY completed_at, id"
        )
    )


def downgrade() -> None:
    tables = set(sa.inspect(op.get_bind()).get_table_names())
    if "ai_assistant_memory_completion" in tables:
        op.drop_table("ai_assistant_memory_completion")
    if "ai_assistant_memory_cursor" in tables:
        op.drop_table("ai_assistant_memory_cursor")


def _create_cursor() -> None:
    op.create_table(
        "ai_assistant_memory_cursor",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("workspace_id", sa.String(128), nullable=False),
        sa.Column("last_processed_run_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("last_processed_completion_id", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("pending_completion_ids", sa.JSON(), nullable=True),
        sa.Column("pending_run_ids", sa.JSON(), nullable=True),
        sa.Column("pending_batch_key", sa.String(128), nullable=True),
        sa.Column("pending_source_hash", sa.String(128), nullable=True),
        sa.Column("pending_input_hash", sa.String(128), nullable=True),
        sa.Column("pending_target_hash", sa.String(128), nullable=True),
        sa.Column("claim_token", sa.String(128), nullable=True),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="IDLE"),
        sa.Column("last_error", sa.String(1000), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("user_id", "workspace_id", name="idx_ai_assistant_memory_cursor_scope"),
    )


def _create_completion_ledger() -> None:
    op.create_table(
        "ai_assistant_memory_completion",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("workspace_id", sa.String(128), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("run_id", name="idx_ai_assistant_memory_completion_run"),
    )
    op.create_index(
        "idx_ai_assistant_memory_completion_scope",
        "ai_assistant_memory_completion",
        ["user_id", "workspace_id", "id"],
    )
