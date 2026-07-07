"""workflow node run selection state

Revision ID: 0025_workflow_node_run_selection_state
Revises: 0024_customer_assistant_worker_profile_skill_refs
Create Date: 2026-07-04 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0025_workflow_node_run_selection_state"
down_revision: str | None = "0024_customer_assistant_worker_profile_skill_refs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workflow_node_run" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("workflow_node_run")}
    if "selection_state" not in columns:
        with op.batch_alter_table("workflow_node_run") as batch_op:
            batch_op.add_column(sa.Column("selection_state", sa.JSON(), nullable=True))
    op.execute(
        sa.text(
            """
            UPDATE workflow_node_run
            SET selection_state = JSON_OBJECT(
                'nodeKey', node_key,
                'state',
                CASE UPPER(status)
                    WHEN 'SUCCEEDED' THEN 'completed'
                    WHEN 'COMPLETED' THEN 'completed'
                    WHEN 'WAITING' THEN 'waiting'
                    WHEN 'RUNNING' THEN 'running'
                    WHEN 'FAILED' THEN 'failed'
                    WHEN 'CANCELLED' THEN 'cancelled'
                    WHEN 'SKIPPED' THEN 'skipped'
                    ELSE 'pending'
                END
            )
            WHERE selection_state IS NULL
            """
        )
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "workflow_node_run" not in inspector.get_table_names():
        return
    columns = {column["name"] for column in inspector.get_columns("workflow_node_run")}
    if "selection_state" in columns:
        with op.batch_alter_table("workflow_node_run") as batch_op:
            batch_op.drop_column("selection_state")
