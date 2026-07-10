"""ai assistant durable tool circuit breaker

Revision ID: 0030_ai_assistant_tool_circuit_breaker
Revises: 0029_ai_assistant_tool_operation_release
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0030_ai_assistant_tool_circuit_breaker"
down_revision: str | None = "0029_ai_assistant_tool_operation_release"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "ai_assistant_tool_circuit_breaker" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "ai_assistant_tool_circuit_breaker",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("breaker_key", sa.String(length=300), nullable=False),
        sa.Column("provider", sa.String(length=120), nullable=False),
        sa.Column("tool_name", sa.String(length=120), nullable=False),
        sa.Column("adapter_name", sa.String(length=120), nullable=False),
        sa.Column("risk_class", sa.String(length=40), nullable=False),
        sa.Column("error_class", sa.String(length=120), nullable=False),
        sa.Column("state", sa.String(length=30), nullable=False, server_default="CLOSED"),
        sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("opened_reason", sa.String(length=500), nullable=True),
        sa.Column("opened_at", sa.DateTime(), nullable=True),
        sa.Column("cooldown_until", sa.DateTime(), nullable=True),
        sa.Column("last_attempt_id", sa.String(length=128), nullable=True),
        sa.Column("actor", sa.String(length=160), nullable=True),
        sa.Column("audit_span_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("breaker_key", name="idx_ai_assistant_tool_circuit_breaker_key"),
    )


def downgrade() -> None:
    if "ai_assistant_tool_circuit_breaker" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("ai_assistant_tool_circuit_breaker")
