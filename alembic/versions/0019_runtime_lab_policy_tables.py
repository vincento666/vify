"""runtime lab and policy tables

Revision ID: 0019_runtime_lab_policy_tables
Revises: 0018_customer_assistant_event_actor
Create Date: 2026-06-15 14:10:00.000000
"""

from collections.abc import Sequence

from alembic import op

from app.modules.runtime_lab.infra.schema import runtime_lab_tables
from app.modules.runtime_policy.infra.schema import runtime_policy_tables


revision: str = "0019_runtime_lab_policy_tables"
down_revision: str | None = "0018_customer_assistant_event_actor"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in [*runtime_lab_tables(), *runtime_policy_tables()]:
        table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed([*runtime_policy_tables(), *runtime_lab_tables()]):
        table.drop(bind=bind, checkfirst=True)
