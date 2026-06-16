import sqlalchemy as sa

from app.core.database import Base
from app.core.schema import BIGINT, deleted_column, id_column, timestamps


def register_customer_assistant_tables(metadata: sa.MetaData | None = None) -> None:
    target = metadata or Base.metadata
    if "customer_assistant_session" not in target.tables:
        sa.Table(
            "customer_assistant_session",
            target,
            id_column(),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            sa.Column("context_json", sa.JSON(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            deleted_column(),
            *timestamps(),
        )

    if "customer_assistant_run" not in target.tables:
        sa.Table(
            "customer_assistant_run",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("idempotency_key", sa.String(160), nullable=True),
            sa.Column("request_hash", sa.String(128), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="RUNNING"),
            sa.Column("input_payload", sa.JSON(), nullable=True),
            sa.Column("response_payload", sa.JSON(), nullable=True),
            sa.Column("warnings_json", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint(
                "session_id",
                "idempotency_key",
                name="idx_customer_assistant_run_idempotency",
            ),
            sa.Index("idx_customer_assistant_run_session", "session_id"),
        )

    if "customer_assistant_task" not in target.tables:
        sa.Table(
            "customer_assistant_task",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("task_key", sa.String(120), nullable=False),
            sa.Column("task_type", sa.String(60), nullable=False),
            sa.Column("business_key", sa.String(160), nullable=False, server_default=""),
            sa.Column("short_id", sa.String(40), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("worker_type", sa.String(60), nullable=False),
            sa.Column("worker_ref", sa.String(160), nullable=False, server_default=""),
            sa.Column("checkpoint_json", sa.JSON(), nullable=True),
            sa.Column("input_snapshot_json", sa.JSON(), nullable=True),
            sa.Column("last_result_json", sa.JSON(), nullable=True),
            sa.Column("proposed_actions_json", sa.JSON(), nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("session_id", "task_key", name="idx_customer_assistant_task_key"),
            sa.Index("idx_customer_assistant_task_session", "session_id"),
            sa.Index("idx_customer_assistant_task_status", "session_id", "status"),
        )

    if "customer_assistant_event" not in target.tables:
        sa.Table(
            "customer_assistant_event",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(80), nullable=False),
            sa.Column("visibility", sa.String(30), nullable=False, server_default="operator"),
            sa.Column("source", sa.String(80), nullable=False, server_default="customer_assistant"),
            sa.Column("actor", sa.String(30), nullable=False, server_default="customer"),
            sa.Column("task_id", BIGINT, nullable=True),
            sa.Column("parent_span_id", sa.String(120), nullable=True),
            sa.Column("span_id", sa.String(120), nullable=True),
            sa.Column("payload", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("session_id", "sequence", name="idx_customer_assistant_event_sequence"),
            sa.Index("idx_customer_assistant_event_session", "session_id"),
            sa.Index("idx_customer_assistant_event_run", "run_id"),
        )

    if "customer_assistant_worker_run" not in target.tables:
        sa.Table(
            "customer_assistant_worker_run",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("parent_run_id", BIGINT, nullable=False),
            sa.Column("task_id", BIGINT, nullable=False),
            sa.Column("worker_type", sa.String(60), nullable=False),
            sa.Column("worker_ref", sa.String(160), nullable=False, server_default=""),
            sa.Column("idempotency_key", sa.String(220), nullable=False),
            sa.Column("request_hash", sa.String(128), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
            sa.Column("input_payload", sa.JSON(), nullable=True),
            sa.Column("result_payload", sa.JSON(), nullable=True),
            sa.Column("error_json", sa.JSON(), nullable=True),
            sa.Column("queued_at", sa.DateTime(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("idempotency_key", name="idx_customer_assistant_worker_run_idempotency"),
            sa.Index("idx_customer_assistant_worker_run_parent", "parent_run_id"),
            sa.Index("idx_customer_assistant_worker_run_task", "task_id"),
            sa.Index("idx_customer_assistant_worker_run_status", "status"),
        )

    if "customer_assistant_worker_event" not in target.tables:
        sa.Table(
            "customer_assistant_worker_event",
            target,
            id_column(),
            sa.Column("worker_run_id", BIGINT, nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(80), nullable=False),
            sa.Column("visibility", sa.String(30), nullable=False, server_default="debug"),
            sa.Column("source", sa.String(80), nullable=False, server_default="customer_assistant_worker"),
            sa.Column("actor", sa.String(30), nullable=False, server_default="system"),
            sa.Column("payload", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("worker_run_id", "sequence", name="idx_customer_assistant_worker_event_sequence"),
            sa.Index("idx_customer_assistant_worker_event_run", "worker_run_id"),
        )

    if "customer_assistant_proposed_action" not in target.tables:
        sa.Table(
            "customer_assistant_proposed_action",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("task_id", BIGINT, nullable=True),
            sa.Column("action_key", sa.String(220), nullable=False),
            sa.Column("action_type", sa.String(80), nullable=False),
            sa.Column("title", sa.String(200), nullable=False, server_default=""),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("result_json", sa.JSON(), nullable=True),
            sa.Column("confirmed_at", sa.DateTime(), nullable=True),
            sa.Column("rejected_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("session_id", "action_key", name="idx_customer_assistant_action_key"),
            sa.Index("idx_customer_assistant_action_session", "session_id"),
            sa.Index("idx_customer_assistant_action_status", "session_id", "status"),
        )

    if "customer_assistant_worker_profile" not in target.tables:
        sa.Table(
            "customer_assistant_worker_profile",
            target,
            id_column(),
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
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("profile_id", name="idx_customer_assistant_worker_profile_id"),
            sa.Index("idx_customer_assistant_worker_profile_task", "task_key"),
            sa.Index("idx_customer_assistant_worker_profile_enabled", "enabled"),
        )


def customer_assistant_tables() -> list[sa.Table]:
    register_customer_assistant_tables()
    names = [
        "customer_assistant_session",
        "customer_assistant_run",
        "customer_assistant_task",
        "customer_assistant_event",
        "customer_assistant_worker_run",
        "customer_assistant_worker_event",
        "customer_assistant_proposed_action",
        "customer_assistant_worker_profile",
    ]
    return [Base.metadata.tables[name] for name in names]
