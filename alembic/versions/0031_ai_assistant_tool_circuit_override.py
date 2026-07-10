"""ai assistant tool circuit override audit

Revision ID: 0031_ai_assistant_tool_circuit_override
Revises: 0030_ai_assistant_tool_circuit_breaker
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0031_ai_assistant_tool_circuit_override"
down_revision: str | None = "0030_ai_assistant_tool_circuit_breaker"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "ai_assistant_tool_circuit_override" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "ai_assistant_tool_circuit_override",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("breaker_key", sa.String(length=300), nullable=False),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("previous_state", sa.String(length=30), nullable=False),
        sa.Column("next_state", sa.String(length=30), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("audit_span_id", sa.String(length=160), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("idx_ai_assistant_tool_circuit_override_key", "ai_assistant_tool_circuit_override", ["breaker_key"])


def downgrade() -> None:
    if "ai_assistant_tool_circuit_override" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("ai_assistant_tool_circuit_override")
