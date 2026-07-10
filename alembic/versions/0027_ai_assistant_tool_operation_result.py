"""ai assistant tool operation result

Revision ID: 0027_ai_assistant_tool_operation_result
Revises: 0026_ai_assistant_tool_ledger
Create Date: 2026-07-10 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0027_ai_assistant_tool_operation_result"
down_revision: str | None = "0026_ai_assistant_tool_ledger"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_assistant_tool_operation" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_assistant_tool_operation")}
    if "output_payload" not in columns:
        with op.batch_alter_table("ai_assistant_tool_operation") as batch_op:
            batch_op.add_column(sa.Column("output_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "ai_assistant_tool_operation" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("ai_assistant_tool_operation")}
    if "output_payload" in columns:
        with op.batch_alter_table("ai_assistant_tool_operation") as batch_op:
            batch_op.drop_column("output_payload")
