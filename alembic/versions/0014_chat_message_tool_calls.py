"""chat message tool calls

Revision ID: 0014_chat_message_tool_calls
Revises: 0013_knowledge_faq
Create Date: 2026-06-04 00:20:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0014_chat_message_tool_calls"
down_revision: str | None = "0013_knowledge_faq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if "tool_calls" not in _columns("chat_message"):
        op.add_column("chat_message", sa.Column("tool_calls", sa.JSON(), nullable=True))


def downgrade() -> None:
    if "tool_calls" in _columns("chat_message"):
        op.drop_column("chat_message", "tool_calls")


def _columns(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}
