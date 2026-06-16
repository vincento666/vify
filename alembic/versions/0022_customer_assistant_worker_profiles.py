"""customer assistant worker profiles

Revision ID: 0022_customer_assistant_worker_profiles
Revises: 0021_chatflow_event_sequence_unique
Create Date: 2026-06-17 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0022_customer_assistant_worker_profiles"
down_revision: str | None = "0021_chatflow_event_sequence_unique"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

BIGINT = sa.BigInteger().with_variant(sa.Integer, "sqlite")


def upgrade() -> None:
    bind = op.get_bind()
    if "customer_assistant_worker_profile" in sa.inspect(bind).get_table_names():
        return
    op.create_table(
        "customer_assistant_worker_profile",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("profile_id", sa.String(120), nullable=False),
        sa.Column("task_key", sa.String(120), nullable=False),
        sa.Column("task_type", sa.String(60), nullable=False),
        sa.Column("worker_type", sa.String(60), nullable=False),
        sa.Column("worker_ref", sa.String(160), nullable=False, server_default=""),
        sa.Column("model_policy_ref", sa.String(160), nullable=False, server_default="default"),
        sa.Column("prompt_ref", sa.String(160), nullable=False, server_default="default"),
        sa.Column("tool_refs", sa.JSON(), nullable=True),
        sa.Column("risk_policy_ref", sa.String(160), nullable=False, server_default="manual_confirm"),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("profile_id", name="idx_customer_assistant_worker_profile_id"),
        sa.Index("idx_customer_assistant_worker_profile_task", "task_key"),
        sa.Index("idx_customer_assistant_worker_profile_enabled", "enabled"),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if "customer_assistant_worker_profile" not in sa.inspect(bind).get_table_names():
        return
    op.drop_table("customer_assistant_worker_profile")
