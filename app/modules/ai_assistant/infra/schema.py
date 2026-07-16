import sqlalchemy as sa

from app.core.database import Base
from app.core.schema import deleted_column, id_column, timestamps
from app.modules.ai_assistant.domain.access_scope import local_ai_assistant_scope


BIGINT = sa.BigInteger()


def register_ai_assistant_tables(metadata: sa.MetaData | None = None) -> None:
    target = metadata or Base.metadata
    if "ai_assistant_session" not in target.tables:
        sa.Table(
            "ai_assistant_session",
            target,
            id_column(),
            sa.Column("user_id", sa.String(120), nullable=False, server_default="local-user"),
            sa.Column(
                "workspace_id",
                sa.String(128),
                nullable=False,
                server_default=local_ai_assistant_scope().workspace_id,
            ),
            sa.Column("title", sa.String(200), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            sa.Column("context_json", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_session_status", "status"),
            sa.Index(
                "idx_ai_assistant_session_scope",
                "user_id",
                "workspace_id",
                "deleted",
            ),
        )

    if "ai_assistant_run" not in target.tables:
        sa.Table(
            "ai_assistant_run",
            target,
            id_column(),
            sa.Column("user_id", sa.String(120), nullable=False, server_default="local-user"),
            sa.Column(
                "workspace_id",
                sa.String(128),
                nullable=False,
                server_default=local_ai_assistant_scope().workspace_id,
            ),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("idempotency_key", sa.String(160), nullable=True),
            sa.Column("request_hash", sa.String(128), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="RUNNING"),
            sa.Column("input_payload", sa.JSON(), nullable=True),
            sa.Column("response_payload", sa.JSON(), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("session_id", "idempotency_key", name="idx_ai_assistant_run_idempotency"),
            sa.Index("idx_ai_assistant_run_session", "session_id"),
            sa.Index(
                "idx_ai_assistant_run_scope",
                "user_id",
                "workspace_id",
                "session_id",
                "deleted",
            ),
        )

    if "ai_assistant_message" not in target.tables:
        sa.Table(
            "ai_assistant_message",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=True),
            sa.Column("role", sa.String(30), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_message_session", "session_id"),
            sa.Index("idx_ai_assistant_message_run", "run_id"),
        )

    if "ai_assistant_event" not in target.tables:
        sa.Table(
            "ai_assistant_event",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("task_id", BIGINT, nullable=True),
            sa.Column("tool_call_id", BIGINT, nullable=True),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("type", sa.String(100), nullable=False),
            sa.Column("level", sa.String(30), nullable=False, server_default="info"),
            sa.Column("status", sa.String(30), nullable=False, server_default="COMPLETED"),
            sa.Column("visible_title", sa.String(200), nullable=False, server_default=""),
            sa.Column("visible_summary", sa.Text(), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("correlation_ids", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("run_id", "sequence", name="idx_ai_assistant_event_run_sequence"),
            sa.Index("idx_ai_assistant_event_run", "run_id"),
            sa.Index("idx_ai_assistant_event_session", "session_id"),
        )

    if "ai_assistant_tool_call" not in target.tables:
        sa.Table(
            "ai_assistant_tool_call",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("tool_name", sa.String(120), nullable=False),
            sa.Column("input_payload", sa.JSON(), nullable=True),
            sa.Column("output_payload", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("duration_ms", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_tool_call_run", "run_id"),
            sa.Index("idx_ai_assistant_tool_call_session", "session_id"),
        )

    if "ai_assistant_approval" not in target.tables:
        sa.Table(
            "ai_assistant_approval",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("tool_name", sa.String(120), nullable=False),
            sa.Column("risk_level", sa.String(40), nullable=False),
            sa.Column("input_payload", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("decided_by", sa.String(120), nullable=True),
            sa.Column("decision_reason", sa.String(500), nullable=True),
            sa.Column("decided_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_approval_status", "status"),
            sa.Index("idx_ai_assistant_approval_run", "run_id"),
        )

    if "ai_assistant_proposed_action" not in target.tables:
        sa.Table(
            "ai_assistant_proposed_action",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("approval_id", BIGINT, nullable=True),
            sa.Column("action_type", sa.String(120), nullable=False),
            sa.Column("title", sa.String(200), nullable=False, server_default=""),
            sa.Column("payload", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_proposed_action_run", "run_id"),
            sa.Index("idx_ai_assistant_proposed_action_status", "status"),
        )

    if "ai_assistant_resource_lock" not in target.tables:
        sa.Table(
            "ai_assistant_resource_lock",
            target,
            id_column(),
            sa.Column("resource_key", sa.String(500), nullable=False),
            sa.Column("mode", sa.String(20), nullable=False),
            sa.Column("owner_session_id", BIGINT, nullable=False),
            sa.Column("owner_run_id", BIGINT, nullable=False),
            sa.Column("owner_tool_call_id", BIGINT, nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(), nullable=False),
            sa.Column("fencing_token", sa.Integer(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_resource_lock_key", "resource_key"),
            sa.Index("idx_ai_assistant_resource_lock_status", "status"),
            sa.Index("idx_ai_assistant_resource_lock_owner", "owner_session_id", "owner_run_id"),
        )

    if "ai_assistant_tool_operation" not in target.tables:
        sa.Table(
            "ai_assistant_tool_operation",
            target,
            id_column(),
            sa.Column("operation_id", sa.String(128), nullable=False),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("plan_step_id", sa.String(160), nullable=False),
            sa.Column("tool_name", sa.String(120), nullable=False),
            sa.Column("effect_class", sa.String(40), nullable=False),
            sa.Column("idempotency_key", sa.String(160), nullable=True),
            sa.Column("request_hash", sa.String(128), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("response_hash", sa.String(128), nullable=True),
            sa.Column("output_payload", sa.JSON(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("retention_until", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("operation_id", name="idx_ai_assistant_tool_operation_id"),
            sa.Index("idx_ai_assistant_tool_operation_run", "run_id"),
            sa.Index("idx_ai_assistant_tool_operation_session", "session_id"),
            sa.Index("idx_ai_assistant_tool_operation_status", "status"),
        )

    if "ai_assistant_tool_attempt" not in target.tables:
        sa.Table(
            "ai_assistant_tool_attempt",
            target,
            id_column(),
            sa.Column("operation_id", sa.String(128), nullable=False),
            sa.Column("attempt_id", sa.String(128), nullable=False),
            sa.Column("adapter_name", sa.String(120), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="PENDING"),
            sa.Column("request_hash", sa.String(128), nullable=False),
            sa.Column("response_hash", sa.String(128), nullable=True),
            sa.Column("error_class", sa.String(120), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("attempt_id", name="idx_ai_assistant_tool_attempt_id"),
            sa.Index("idx_ai_assistant_tool_attempt_operation", "operation_id"),
            sa.Index("idx_ai_assistant_tool_attempt_status", "status"),
        )

    if "ai_assistant_tool_operation_release" not in target.tables:
        sa.Table(
            "ai_assistant_tool_operation_release",
            target,
            id_column(),
            sa.Column("operation_id", sa.String(128), nullable=False),
            sa.Column("authority", sa.String(40), nullable=False),
            sa.Column("actor", sa.String(160), nullable=False),
            sa.Column("reason", sa.String(500), nullable=False),
            sa.Column("evidence_ref", sa.String(500), nullable=False),
            sa.Column("previous_status", sa.String(30), nullable=False),
            sa.Column("next_status", sa.String(30), nullable=False),
            *timestamps(),
            sa.Index("idx_ai_assistant_tool_operation_release_operation", "operation_id"),
        )

    if "ai_assistant_tool_circuit_breaker" not in target.tables:
        sa.Table(
            "ai_assistant_tool_circuit_breaker",
            target,
            id_column(),
            sa.Column("breaker_key", sa.String(300), nullable=False),
            sa.Column("provider", sa.String(120), nullable=False),
            sa.Column("tool_name", sa.String(120), nullable=False),
            sa.Column("adapter_name", sa.String(120), nullable=False),
            sa.Column("risk_class", sa.String(40), nullable=False),
            sa.Column("error_class", sa.String(120), nullable=False),
            sa.Column("state", sa.String(30), nullable=False, server_default="CLOSED"),
            sa.Column("failure_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("opened_reason", sa.String(500), nullable=True),
            sa.Column("opened_at", sa.DateTime(), nullable=True),
            sa.Column("cooldown_until", sa.DateTime(), nullable=True),
            sa.Column("last_attempt_id", sa.String(128), nullable=True),
            sa.Column("actor", sa.String(160), nullable=True),
            sa.Column("audit_span_id", sa.String(160), nullable=True),
            *timestamps(),
            sa.UniqueConstraint("breaker_key", name="idx_ai_assistant_tool_circuit_breaker_key"),
        )

    if "ai_assistant_tool_circuit_override" not in target.tables:
        sa.Table(
            "ai_assistant_tool_circuit_override",
            target,
            id_column(),
            sa.Column("breaker_key", sa.String(300), nullable=False),
            sa.Column("actor", sa.String(160), nullable=False),
            sa.Column("previous_state", sa.String(30), nullable=False),
            sa.Column("next_state", sa.String(30), nullable=False),
            sa.Column("reason", sa.String(500), nullable=False),
            sa.Column("audit_span_id", sa.String(160), nullable=True),
            *timestamps(),
            sa.Index("idx_ai_assistant_tool_circuit_override_key", "breaker_key"),
        )

    if "ai_assistant_memory_cursor" not in target.tables:
        sa.Table(
            "ai_assistant_memory_cursor",
            target,
            id_column(),
            sa.Column("user_id", sa.String(120), nullable=False),
            sa.Column("workspace_id", sa.String(128), nullable=False),
            sa.Column("last_processed_run_id", BIGINT, nullable=False, server_default="0"),
            sa.Column("last_processed_completion_id", BIGINT, nullable=False, server_default="0"),
            sa.Column("pending_completion_ids", sa.JSON(), nullable=True),
            sa.Column("pending_run_ids", sa.JSON(), nullable=True),
            sa.Column("pending_batch_key", sa.String(128), nullable=True),
            sa.Column("pending_source_hash", sa.String(128), nullable=True),
            sa.Column("pending_input_hash", sa.String(128), nullable=True),
            sa.Column("pending_target_hash", sa.String(128), nullable=True),
            sa.Column("claim_token", sa.String(128), nullable=True),
            sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False, server_default="IDLE"),
            sa.Column("last_error", sa.String(1000), nullable=True),
            *timestamps(),
            sa.UniqueConstraint(
                "user_id",
                "workspace_id",
                name="idx_ai_assistant_memory_cursor_scope",
            ),
        )

    if "ai_assistant_memory_completion" not in target.tables:
        sa.Table(
            "ai_assistant_memory_completion",
            target,
            id_column(),
            sa.Column("user_id", sa.String(120), nullable=False),
            sa.Column("workspace_id", sa.String(128), nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=False),
            *timestamps(),
            sa.UniqueConstraint("run_id", name="idx_ai_assistant_memory_completion_run"),
            sa.Index(
                "idx_ai_assistant_memory_completion_scope",
                "user_id",
                "workspace_id",
                "id",
            ),
        )

    if "ai_assistant_model_usage" not in target.tables:
        sa.Table(
            "ai_assistant_model_usage",
            target,
            id_column(),
            sa.Column("user_id", sa.String(120), nullable=False),
            sa.Column("workspace_id", sa.String(128), nullable=False),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("call_id", sa.String(160), nullable=False),
            sa.Column("call_kind", sa.String(40), nullable=False),
            sa.Column("provider", sa.String(120), nullable=False),
            sa.Column("model", sa.String(240), nullable=False),
            sa.Column("input_tokens", BIGINT, nullable=True),
            sa.Column("output_tokens", BIGINT, nullable=True),
            sa.Column("cache_read_tokens", BIGINT, nullable=True),
            sa.Column("cache_write_tokens", BIGINT, nullable=True),
            sa.Column("reasoning_tokens", BIGINT, nullable=True),
            sa.Column("total_tokens", BIGINT, nullable=True),
            sa.Column("usage_source", sa.String(30), nullable=False, server_default="pending"),
            sa.Column("provider_cost_usd", sa.Numeric(20, 10), nullable=True),
            sa.Column("estimated_cost_usd", sa.Numeric(20, 10), nullable=True),
            sa.Column("effective_cost_usd", sa.Numeric(20, 10), nullable=True),
            sa.Column("cost_source", sa.String(30), nullable=False, server_default="unknown"),
            sa.Column("pricing_version", sa.String(120), nullable=True),
            sa.Column("started_at", sa.DateTime(), nullable=False),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            *timestamps(),
            sa.UniqueConstraint(
                "user_id",
                "workspace_id",
                "run_id",
                "call_id",
                name="uq_ai_assistant_model_usage_call",
            ),
            sa.Index(
                "idx_ai_assistant_model_usage_scope_time",
                "user_id",
                "workspace_id",
                "started_at",
            ),
            sa.Index(
                "idx_ai_assistant_model_usage_session",
                "user_id",
                "workspace_id",
                "session_id",
                "started_at",
            ),
        )


def ai_assistant_tables() -> list[sa.Table]:
    register_ai_assistant_tables()
    names = [
        "ai_assistant_session",
        "ai_assistant_run",
        "ai_assistant_message",
        "ai_assistant_event",
        "ai_assistant_tool_call",
        "ai_assistant_approval",
        "ai_assistant_proposed_action",
        "ai_assistant_resource_lock",
        "ai_assistant_tool_operation",
        "ai_assistant_tool_attempt",
        "ai_assistant_tool_operation_release",
        "ai_assistant_tool_circuit_breaker",
        "ai_assistant_tool_circuit_override",
        "ai_assistant_memory_cursor",
        "ai_assistant_memory_completion",
        "ai_assistant_model_usage",
    ]
    return [Base.metadata.tables[name] for name in names]
