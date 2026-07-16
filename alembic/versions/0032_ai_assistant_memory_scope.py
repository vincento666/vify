"""ai assistant memory access scope

Revision ID: 0032_ai_assistant_memory_scope
Revises: 0031_ai_assistant_tool_circuit_override
Create Date: 2026-07-11 00:00:00.000000
"""

from collections.abc import Sequence
from hashlib import sha256
import os
from pathlib import Path

from alembic import op
import sqlalchemy as sa


revision: str = "0032_ai_assistant_memory_scope"
down_revision: str | None = "0031_ai_assistant_tool_circuit_override"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    _add_scope(
        "ai_assistant_session",
        "idx_ai_assistant_session_scope",
        ["user_id", "workspace_id", "deleted"],
    )
    _add_scope(
        "ai_assistant_run",
        "idx_ai_assistant_run_scope",
        ["user_id", "workspace_id", "session_id", "deleted"],
    )
def downgrade() -> None:
    _drop_scope("ai_assistant_run", "idx_ai_assistant_run_scope")
    _drop_scope("ai_assistant_session", "idx_ai_assistant_session_scope")


def _add_scope(table_name: str, index_name: str, index_columns: list[str]) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    with op.batch_alter_table(table_name) as batch_op:
        if "user_id" not in columns:
            batch_op.add_column(
                sa.Column("user_id", sa.String(120), nullable=False, server_default="local-user")
            )
        if "workspace_id" not in columns:
            batch_op.add_column(
                sa.Column(
                    "workspace_id",
                    sa.String(128),
                    nullable=False,
                    server_default=_local_workspace_id(),
                )
            )
        if index_name not in indexes:
            batch_op.create_index(index_name, index_columns)


def _drop_scope(table_name: str, index_name: str) -> None:
    inspector = sa.inspect(op.get_bind())
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    indexes = {index["name"] for index in inspector.get_indexes(table_name)}
    with op.batch_alter_table(table_name) as batch_op:
        if index_name in indexes:
            batch_op.drop_index(index_name)
        if "workspace_id" in columns:
            batch_op.drop_column("workspace_id")
        if "user_id" in columns:
            batch_op.drop_column("user_id")


def _local_workspace_id() -> str:
    root = Path(os.environ.get("HIFY_WORKSPACE_ROOT") or os.getcwd()).expanduser().resolve()
    return sha256(str(root).encode()).hexdigest()
