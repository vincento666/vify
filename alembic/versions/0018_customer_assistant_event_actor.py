"""customer assistant event actor

Revision ID: 0018_customer_assistant_event_actor
Revises: 0017_customer_assistant_runtime
Create Date: 2026-06-15 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0018_customer_assistant_event_actor"
down_revision: str | None = "0017_customer_assistant_runtime"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if _has_table("customer_assistant_event") and not _has_column("customer_assistant_event", "actor"):
        op.add_column(
            "customer_assistant_event",
            sa.Column("actor", sa.String(length=30), nullable=False, server_default="customer"),
        )


def downgrade() -> None:
    if _has_table("customer_assistant_event") and _has_column("customer_assistant_event", "actor"):
        op.drop_column("customer_assistant_event", "actor")


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    return column_name in {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}
