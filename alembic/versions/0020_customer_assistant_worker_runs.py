"""customer assistant worker runs

Revision ID: 0020_customer_assistant_worker_runs
Revises: 0019_runtime_lab_policy_tables
Create Date: 2026-06-16 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

from app.modules.customer_assistant.infra.schema import customer_assistant_tables


revision: str = "0020_customer_assistant_worker_runs"
down_revision: str | None = "0019_runtime_lab_policy_tables"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in customer_assistant_tables():
        if table.name in {"customer_assistant_worker_run", "customer_assistant_worker_event"}:
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(customer_assistant_tables()):
        if table.name in {"customer_assistant_worker_run", "customer_assistant_worker_event"}:
            table.drop(bind=bind, checkfirst=True)
