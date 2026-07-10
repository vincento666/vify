"""ai assistant tool operation unknown retention

Revision ID: 0028_ai_assistant_tool_operation_unknown
Revises: 0027_ai_assistant_tool_operation_result
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0028_ai_assistant_tool_operation_unknown"
down_revision: str | None = "0027_ai_assistant_tool_operation_result"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_assistant_tool_operation" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_assistant_tool_operation")}
    if "retention_until" not in columns:
        with op.batch_alter_table("ai_assistant_tool_operation") as batch_op:
            batch_op.add_column(sa.Column("retention_until", sa.DateTime(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_assistant_tool_operation" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_assistant_tool_operation")}
    if "retention_until" in columns:
        with op.batch_alter_table("ai_assistant_tool_operation") as batch_op:
            batch_op.drop_column("retention_until")
