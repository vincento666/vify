"""customer assistant worker profile skill refs

Revision ID: 0024_customer_assistant_worker_profile_skill_refs
Revises: 0023_customer_assistant_worker_profile_scope
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0024_customer_assistant_worker_profile_skill_refs"
down_revision: str | None = "0023_customer_assistant_worker_profile_scope"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "customer_assistant_worker_profile" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("customer_assistant_worker_profile")}
    with op.batch_alter_table("customer_assistant_worker_profile") as batch_op:
        if "tool_policy_ref" not in columns:
            batch_op.add_column(
                sa.Column(
                    "tool_policy_ref",
                    sa.String(160),
                    nullable=False,
                    server_default="customer_assistant_worker_tool_default",
                )
            )
        if "output_schema_ref" not in columns:
            batch_op.add_column(
                sa.Column(
                    "output_schema_ref",
                    sa.String(160),
                    nullable=False,
                    server_default="customer_assistant_worker_result_v1",
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "customer_assistant_worker_profile" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("customer_assistant_worker_profile")}
    with op.batch_alter_table("customer_assistant_worker_profile") as batch_op:
        if "output_schema_ref" in columns:
            batch_op.drop_column("output_schema_ref")
        if "tool_policy_ref" in columns:
            batch_op.drop_column("tool_policy_ref")
