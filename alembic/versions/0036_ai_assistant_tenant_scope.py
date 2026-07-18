"""add explicit tenant scope to AI Assistant durable state

Revision ID: 0036_ai_assistant_tenant_scope
Revises: 0035_runtime_job_owner_identity
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0036_ai_assistant_tenant_scope"
down_revision: str | None = "0035_runtime_job_owner_identity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_INDEXES = {
    "ai_assistant_session": {
        "idx_ai_assistant_session_scope": (
            False,
            ["tenant_id", "user_id", "workspace_id", "deleted"],
            ["user_id", "workspace_id", "deleted"],
        ),
    },
    "ai_assistant_run": {
        "idx_ai_assistant_run_scope": (
            False,
            ["tenant_id", "user_id", "workspace_id", "session_id", "deleted"],
            ["user_id", "workspace_id", "session_id", "deleted"],
        ),
    },
    "ai_assistant_memory_cursor": {
        "idx_ai_assistant_memory_cursor_scope": (
            True,
            ["tenant_id", "user_id", "workspace_id"],
            ["user_id", "workspace_id"],
        ),
    },
    "ai_assistant_memory_completion": {
        "idx_ai_assistant_memory_completion_scope": (
            False,
            ["tenant_id", "user_id", "workspace_id", "id"],
            ["user_id", "workspace_id", "id"],
        ),
    },
    "ai_assistant_model_usage": {
        "uq_ai_assistant_model_usage_call": (
            True,
            ["tenant_id", "user_id", "workspace_id", "run_id", "call_id"],
            ["user_id", "workspace_id", "run_id", "call_id"],
        ),
        "idx_ai_assistant_model_usage_scope_time": (
            False,
            ["tenant_id", "user_id", "workspace_id", "started_at"],
            ["user_id", "workspace_id", "started_at"],
        ),
        "idx_ai_assistant_model_usage_session": (
            False,
            ["tenant_id", "user_id", "workspace_id", "session_id", "started_at"],
            ["user_id", "workspace_id", "session_id", "started_at"],
        ),
    },
}


def upgrade() -> None:
    for table_name, definitions in _INDEXES.items():
        _replace_scope(table_name, definitions, use_tenant=True)


def downgrade() -> None:
    for table_name, definitions in reversed(tuple(_INDEXES.items())):
        _replace_scope(table_name, definitions, use_tenant=False)


def _replace_scope(
    table_name: str,
    definitions: dict[str, tuple[bool, list[str], list[str]]],
    *,
    use_tenant: bool,
) -> None:
    inspector = sa.inspect(op.get_bind())
    if table_name not in set(inspector.get_table_names()):
        return
    columns = {column["name"] for column in inspector.get_columns(table_name)}
    indexes = {str(index["name"]) for index in inspector.get_indexes(table_name)}
    constraints = {
        str(item["name"])
        for item in inspector.get_unique_constraints(table_name)
        if item.get("name")
    }
    with op.batch_alter_table(table_name) as batch_op:
        for name, (unique, tenant_columns, legacy_columns) in definitions.items():
            existing = constraints if unique else indexes
            if name in existing:
                if unique:
                    batch_op.drop_constraint(name, type_="unique")
                else:
                    batch_op.drop_index(name)
        if use_tenant and "tenant_id" not in columns:
            batch_op.add_column(
                sa.Column(
                    "tenant_id",
                    sa.String(120),
                    nullable=False,
                    server_default="local",
                )
            )
        for name, (unique, tenant_columns, legacy_columns) in definitions.items():
            target_columns = tenant_columns if use_tenant else legacy_columns
            if unique:
                batch_op.create_unique_constraint(name, target_columns)
            else:
                batch_op.create_index(name, target_columns)
        if not use_tenant and "tenant_id" in columns:
            batch_op.drop_column("tenant_id")
