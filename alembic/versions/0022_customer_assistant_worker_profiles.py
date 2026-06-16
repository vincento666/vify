"""customer assistant worker profiles

Revision ID: 0022_customer_assistant_worker_profiles
Revises: 0021_chatflow_event_sequence_unique
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

from app.modules.customer_assistant.infra.schema import customer_assistant_tables


revision: str = "0022_customer_assistant_worker_profiles"
down_revision: str | None = "0021_chatflow_event_sequence_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    for table in customer_assistant_tables():
        if table.name == "customer_assistant_worker_profile":
            table.create(bind=bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    for table in reversed(customer_assistant_tables()):
        if table.name == "customer_assistant_worker_profile":
            table.drop(bind=bind, checkfirst=True)
