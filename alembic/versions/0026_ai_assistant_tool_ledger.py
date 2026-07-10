"""ai assistant tool ledger

Revision ID: 0026_ai_assistant_tool_ledger
Revises: 0025_workflow_node_run_selection_state
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0026_ai_assistant_tool_ledger"
down_revision: str | None = "0025_workflow_node_run_selection_state"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not _has_table("ai_assistant_tool_operation"):
        op.create_table(
            "ai_assistant_tool_operation",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("operation_id", sa.String(length=128), nullable=False),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("run_id", sa.BigInteger(), nullable=False),
            sa.Column("plan_step_id", sa.String(length=160), nullable=False),
            sa.Column("tool_name", sa.String(length=120), nullable=False),
            sa.Column("effect_class", sa.String(length=40), nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=True),
            sa.Column("request_hash", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
            sa.Column("response_hash", sa.String(length=128), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("operation_id", name="idx_ai_assistant_tool_operation_id"),
        )
        op.create_index("idx_ai_assistant_tool_operation_run", "ai_assistant_tool_operation", ["run_id"])
        op.create_index("idx_ai_assistant_tool_operation_session", "ai_assistant_tool_operation", ["session_id"])
        op.create_index("idx_ai_assistant_tool_operation_status", "ai_assistant_tool_operation", ["status"])
    if not _has_table("ai_assistant_tool_attempt"):
        op.create_table(
            "ai_assistant_tool_attempt",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("operation_id", sa.String(length=128), nullable=False),
            sa.Column("attempt_id", sa.String(length=128), nullable=False),
            sa.Column("adapter_name", sa.String(length=120), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
            sa.Column("request_hash", sa.String(length=128), nullable=False),
            sa.Column("response_hash", sa.String(length=128), nullable=True),
            sa.Column("error_class", sa.String(length=120), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("attempt_id", name="idx_ai_assistant_tool_attempt_id"),
        )
        op.create_index("idx_ai_assistant_tool_attempt_operation", "ai_assistant_tool_attempt", ["operation_id"])
        op.create_index("idx_ai_assistant_tool_attempt_status", "ai_assistant_tool_attempt", ["status"])


def downgrade() -> None:
    for table_name in ("ai_assistant_tool_attempt", "ai_assistant_tool_operation"):
        if _has_table(table_name):
            op.drop_table(table_name)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()
