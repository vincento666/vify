"""chatflow event sequence uniqueness

Revision ID: 0021_chatflow_event_sequence_unique
Revises: 0020_customer_assistant_worker_runs
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0021_chatflow_event_sequence_unique"
down_revision: str | None = "0020_customer_assistant_worker_runs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None
CONSTRAINT_NAME = "idx_chatflow_event_run_sequence"


def upgrade() -> None:
    if _has_run_sequence_unique():
        return
    with op.batch_alter_table("chatflow_event") as batch_op:
        batch_op.create_unique_constraint(CONSTRAINT_NAME, ["run_id", "sequence"])


def downgrade() -> None:
    if not _has_run_sequence_unique():
        return
    with op.batch_alter_table("chatflow_event") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="unique")


def _has_run_sequence_unique() -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    constraints = {constraint["name"] for constraint in inspector.get_unique_constraints("chatflow_event")}
    indexes = {index["name"] for index in inspector.get_indexes("chatflow_event")}
    return CONSTRAINT_NAME in constraints or CONSTRAINT_NAME in indexes
