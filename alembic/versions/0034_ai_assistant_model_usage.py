"""ai assistant per-call model usage ledger

Revision ID: 0034_ai_assistant_model_usage
Revises: 0033_ai_assistant_memory_cursor
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0034_ai_assistant_model_usage"
down_revision: str | None = "0033_ai_assistant_memory_cursor"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    if "ai_assistant_model_usage" in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        "ai_assistant_model_usage",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(120), nullable=False),
        sa.Column("workspace_id", sa.String(128), nullable=False),
        sa.Column("session_id", sa.BigInteger(), nullable=False),
        sa.Column("run_id", sa.BigInteger(), nullable=False),
        sa.Column("call_id", sa.String(160), nullable=False),
        sa.Column("call_kind", sa.String(40), nullable=False),
        sa.Column("provider", sa.String(120), nullable=False),
        sa.Column("model", sa.String(240), nullable=False),
        sa.Column("input_tokens", sa.BigInteger(), nullable=True),
        sa.Column("output_tokens", sa.BigInteger(), nullable=True),
        sa.Column("cache_read_tokens", sa.BigInteger(), nullable=True),
        sa.Column("cache_write_tokens", sa.BigInteger(), nullable=True),
        sa.Column("reasoning_tokens", sa.BigInteger(), nullable=True),
        sa.Column("total_tokens", sa.BigInteger(), nullable=True),
        sa.Column("usage_source", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("provider_cost_usd", sa.Numeric(20, 10), nullable=True),
        sa.Column("estimated_cost_usd", sa.Numeric(20, 10), nullable=True),
        sa.Column("effective_cost_usd", sa.Numeric(20, 10), nullable=True),
        sa.Column("cost_source", sa.String(30), nullable=False, server_default="unknown"),
        sa.Column("pricing_version", sa.String(120), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint(
            "user_id",
            "workspace_id",
            "run_id",
            "call_id",
            name="uq_ai_assistant_model_usage_call",
        ),
    )
    op.create_index(
        "idx_ai_assistant_model_usage_scope_time",
        "ai_assistant_model_usage",
        ["user_id", "workspace_id", "started_at"],
    )
    op.create_index(
        "idx_ai_assistant_model_usage_session",
        "ai_assistant_model_usage",
        ["user_id", "workspace_id", "session_id", "started_at"],
    )


def downgrade() -> None:
    if "ai_assistant_model_usage" in set(sa.inspect(op.get_bind()).get_table_names()):
        op.drop_table("ai_assistant_model_usage")
