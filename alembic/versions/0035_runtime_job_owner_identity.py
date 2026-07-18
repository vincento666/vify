"""make runtime job identity owner-aware

Revision ID: 0035_runtime_job_owner_identity
Revises: 0034_ai_assistant_model_usage
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op


revision: str = "0035_runtime_job_owner_identity"
down_revision: str | None = "0034_ai_assistant_model_usage"
branch_labels: str | None = None
depends_on: str | None = None

TABLE_NAME = "runtime_jobs"
OLD_CONSTRAINT = "idx_runtime_jobs_run_type"
NEW_CONSTRAINT = "idx_runtime_jobs_owner_run_type"


def upgrade() -> None:
    if TABLE_NAME not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    constraint_names = _unique_constraint_names()
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if OLD_CONSTRAINT in constraint_names:
            batch_op.drop_constraint(OLD_CONSTRAINT, type_="unique")
        if NEW_CONSTRAINT not in constraint_names:
            batch_op.create_unique_constraint(
                NEW_CONSTRAINT,
                ["owner_type", "run_id", "job_type"],
            )


def downgrade() -> None:
    if TABLE_NAME not in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    constraint_names = _unique_constraint_names()
    with op.batch_alter_table(TABLE_NAME) as batch_op:
        if NEW_CONSTRAINT in constraint_names:
            batch_op.drop_constraint(NEW_CONSTRAINT, type_="unique")
        if OLD_CONSTRAINT not in constraint_names:
            batch_op.create_unique_constraint(OLD_CONSTRAINT, ["run_id", "job_type"])


def _unique_constraint_names() -> set[str]:
    return {
        str(item["name"])
        for item in sa.inspect(op.get_bind()).get_unique_constraints(TABLE_NAME)
        if item.get("name")
    }
