"""chatflow event sequence uniqueness

Revision ID: 0021_chatflow_event_sequence_unique
Revises: 0020_customer_assistant_worker_runs
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op


revision: str = "0021_chatflow_event_sequence_unique"
down_revision: str | None = "0020_customer_assistant_worker_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chatflow_event") as batch_op:
        batch_op.create_unique_constraint("idx_chatflow_event_run_sequence", ["run_id", "sequence"])


def downgrade() -> None:
    with op.batch_alter_table("chatflow_event") as batch_op:
        batch_op.drop_constraint("idx_chatflow_event_run_sequence", type_="unique")
