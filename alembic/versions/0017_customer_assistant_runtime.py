"""customer assistant runtime

Revision ID: 0017_customer_assistant_runtime
Revises: 0016_evaluation_target_evidence
Create Date: 2026-06-13 00:00:00.000000
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0017_customer_assistant_runtime"
down_revision: str | None = "0016_evaluation_target_evidence"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    if not _has_table("customer_assistant_session"):
        op.create_table(
            "customer_assistant_session",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="ACTIVE"),
            sa.Column("context_json", sa.JSON(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
        )
    if not _has_table("customer_assistant_run"):
        op.create_table(
            "customer_assistant_run",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("idempotency_key", sa.String(length=160), nullable=True),
            sa.Column("request_hash", sa.String(length=128), nullable=False),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="RUNNING"),
            sa.Column("input_payload", sa.JSON(), nullable=True),
            sa.Column("response_payload", sa.JSON(), nullable=True),
            sa.Column("warnings_json", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("session_id", "idempotency_key", name="idx_customer_assistant_run_idempotency"),
        )
        op.create_index("idx_customer_assistant_run_session", "customer_assistant_run", ["session_id"])
    if not _has_table("customer_assistant_task"):
        op.create_table(
            "customer_assistant_task",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("task_key", sa.String(length=120), nullable=False),
            sa.Column("task_type", sa.String(length=60), nullable=False),
            sa.Column("business_key", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("short_id", sa.String(length=40), nullable=False, server_default=""),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
            sa.Column("worker_type", sa.String(length=60), nullable=False),
            sa.Column("worker_ref", sa.String(length=160), nullable=False, server_default=""),
            sa.Column("checkpoint_json", sa.JSON(), nullable=True),
            sa.Column("input_snapshot_json", sa.JSON(), nullable=True),
            sa.Column("last_result_json", sa.JSON(), nullable=True),
            sa.Column("proposed_actions_json", sa.JSON(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("session_id", "task_key", name="idx_customer_assistant_task_key"),
        )
        op.create_index("idx_customer_assistant_task_session", "customer_assistant_task", ["session_id"])
        op.create_index("idx_customer_assistant_task_status", "customer_assistant_task", ["session_id", "status"])
    if not _has_table("customer_assistant_event"):
        op.create_table(
            "customer_assistant_event",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("run_id", sa.BigInteger(), nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(length=80), nullable=False),
            sa.Column("visibility", sa.String(length=30), nullable=False, server_default="operator"),
            sa.Column("source", sa.String(length=80), nullable=False, server_default="customer_assistant"),
            sa.Column("task_id", sa.BigInteger(), nullable=True),
            sa.Column("parent_span_id", sa.String(length=120), nullable=True),
            sa.Column("span_id", sa.String(length=120), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("session_id", "sequence", name="idx_customer_assistant_event_sequence"),
        )
        op.create_index("idx_customer_assistant_event_session", "customer_assistant_event", ["session_id"])
        op.create_index("idx_customer_assistant_event_run", "customer_assistant_event", ["run_id"])
    if not _has_table("customer_assistant_proposed_action"):
        op.create_table(
            "customer_assistant_proposed_action",
            sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
            sa.Column("session_id", sa.BigInteger(), nullable=False),
            sa.Column("run_id", sa.BigInteger(), nullable=False),
            sa.Column("task_id", sa.BigInteger(), nullable=True),
            sa.Column("action_key", sa.String(length=220), nullable=False),
            sa.Column("action_type", sa.String(length=80), nullable=False),
            sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False, server_default="PENDING"),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("rejected_at", sa.DateTime(), nullable=True),
            sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint("session_id", "action_key", name="idx_customer_assistant_action_key"),
        )
        op.create_index("idx_customer_assistant_action_session", "customer_assistant_proposed_action", ["session_id"])
        op.create_index(
            "idx_customer_assistant_action_status",
            "customer_assistant_proposed_action",
            ["session_id", "status"],
        )


def downgrade() -> None:
    for table_name in (
        "customer_assistant_proposed_action",
        "customer_assistant_event",
        "customer_assistant_task",
        "customer_assistant_run",
        "customer_assistant_session",
    ):
        if _has_table(table_name):
            op.drop_table(table_name)


def _has_table(table_name: str) -> bool:
    return table_name in sa.inspect(op.get_bind()).get_table_names()
