"""ai assistant tool operation release audit

Revision ID: 0029_ai_assistant_tool_operation_release
Revises: 0028_ai_assistant_tool_operation_unknown
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0029_ai_assistant_tool_operation_release"
down_revision: str | None = "0028_ai_assistant_tool_operation_unknown"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "ai_assistant_tool_operation_release" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "ai_assistant_tool_operation_release",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("operation_id", sa.String(length=128), nullable=False),
        sa.Column("authority", sa.String(length=40), nullable=False),
        sa.Column("actor", sa.String(length=160), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=False),
        sa.Column("evidence_ref", sa.String(length=500), nullable=False),
        sa.Column("previous_status", sa.String(length=30), nullable=False),
        sa.Column("next_status", sa.String(length=30), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "idx_ai_assistant_tool_operation_release_operation",
        "ai_assistant_tool_operation_release",
        ["operation_id"],
    )


def downgrade() -> None:
    if "ai_assistant_tool_operation_release" in sa.inspect(op.get_bind()).get_table_names():
        op.drop_table("ai_assistant_tool_operation_release")
