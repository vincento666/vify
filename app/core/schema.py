from typing import Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.core.database import Base

BIGINT = sa.BigInteger().with_variant(sa.Integer, "sqlite")
DEFAULT_EMBEDDING_DIMENSIONS = 1536
RELATIONAL_VECTOR_TABLES = {"document_embedding", "knowledge_faq_embedding"}


def register_baseline_tables() -> None:
    metadata = Base.metadata
    if "provider" in metadata.tables:
        register_chatflow_state_tables(metadata)
        register_runtime_event_outbox_table(metadata)
        register_chatflow_channel_tables(metadata)
        register_workflow_publish_tables(metadata)
        register_runtime_job_tables(metadata)
        register_handoff_tables(metadata)
        register_audit_tables(metadata)
        register_knowledge_vector_tables(metadata)
        register_knowledge_faq_tables(metadata)
        register_evaluation_tables(metadata)
        register_agent_version_tables(metadata)
        register_agent_publish_tables(metadata)
        register_agent_memory_variable_columns(metadata)
        register_agent_prompt_optimization_tables(metadata)
        register_api_resource_tables(metadata)
        _register_runtime_policy_tables(metadata)
        _register_customer_assistant_tables(metadata)
        _register_ai_assistant_tables(metadata)
        return

    sa.Table(
        "provider",
        metadata,
        id_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("type", sa.String(30), nullable=False),
        sa.Column("base_url", sa.String(500), nullable=False),
        sa.Column("auth_config", sa.JSON(), nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=True),
        enabled_column(),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("name", name="idx_provider_name"),
    )

    sa.Table(
        "model_config",
        metadata,
        id_column(),
        sa.Column("provider_id", BIGINT, nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("model_id", sa.String(100), nullable=False),
        sa.Column("context_size", sa.Integer, nullable=False, server_default="4096"),
        sa.Column("extra_params", sa.JSON(), nullable=True),
        enabled_column(),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_model_config_provider_id", "provider_id"),
    )

    sa.Table(
        "provider_health",
        metadata,
        id_column(),
        sa.Column("provider_id", BIGINT, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="UNKNOWN"),
        sa.Column("last_check_at", sa.DateTime(), nullable=True),
        sa.Column("last_success_at", sa.DateTime(), nullable=True),
        sa.Column("fail_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer, nullable=True),
        sa.Column("error_message", sa.String(500), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("provider_id", name="idx_provider_health_provider_id"),
    )

    sa.Table(
        "mcp_server",
        metadata,
        id_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("endpoint", sa.String(500), nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=True),
        enabled_column(),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("name", name="idx_mcp_server_name"),
    )

    sa.Table(
        "agent",
        metadata,
        id_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=True),
        sa.Column("opening_message", sa.Text(), nullable=True),
        sa.Column("suggested_questions", sa.JSON(), nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("memory", sa.JSON(), nullable=True),
        sa.Column("tool_policies", sa.JSON(), nullable=True),
        sa.Column("model_config_id", BIGINT, nullable=False),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=False, server_default="0.70"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="2048"),
        sa.Column("max_context_turns", sa.Integer, nullable=False, server_default="10"),
        enabled_column(),
        sa.Column("knowledge_base_id", BIGINT, nullable=True),
        sa.Column("knowledge_base_ids", sa.JSON(), nullable=True),
        sa.Column("retrieval_settings", sa.JSON(), nullable=True),
        sa.Column("evaluation_gate", sa.JSON(), nullable=True),
        sa.Column("access", sa.JSON(), nullable=True),
        sa.Column("sharing", sa.JSON(), nullable=True),
        sa.Column("catalog", sa.JSON(), nullable=True),
        sa.Column("analytics", sa.JSON(), nullable=True),
        sa.Column("workflow_id", BIGINT, nullable=True),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("name", name="idx_agent_name"),
        sa.Index("idx_agent_model_config_id", "model_config_id"),
    )

    sa.Table(
        "agent_tool",
        metadata,
        id_column(),
        sa.Column("agent_id", BIGINT, nullable=False),
        sa.Column("mcp_server_id", BIGINT, nullable=False),
        *timestamps(),
        sa.UniqueConstraint("agent_id", "mcp_server_id", name="idx_agent_tool_agent_mcp"),
        sa.Index("idx_agent_tool_mcp_server_id", "mcp_server_id"),
    )

    sa.Table(
        "chat_session",
        metadata,
        id_column(),
        sa.Column("agent_id", BIGINT, nullable=False),
        sa.Column("title", sa.String(200), server_default="", nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="ACTIVE"),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_chat_session_agent_id", "agent_id"),
    )

    sa.Table(
        "chat_message",
        metadata,
        id_column(),
        sa.Column("session_id", BIGINT, nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("tokens", sa.Integer, server_default="0", nullable=True),
        sa.Column("finish_reason", sa.String(50), server_default="", nullable=True),
        sa.Column("latency_ms", sa.Integer, server_default="0", nullable=True),
        sa.Column("tool_calls", sa.JSON(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_chat_message_session_id", "session_id"),
    )

    sa.Table(
        "knowledge_base",
        metadata,
        id_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=True),
        enabled_column(),
        deleted_column(),
        *timestamps(),
    )

    sa.Table(
        "document",
        metadata,
        id_column(),
        sa.Column("knowledge_base_id", BIGINT, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("file_type", sa.String(20), nullable=False),
        sa.Column("file_size", BIGINT, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("error_message", sa.String(500), server_default="", nullable=True),
        sa.Column("chunk_count", sa.Integer, nullable=False, server_default="0"),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_document_knowledge_base_id", "knowledge_base_id"),
    )

    sa.Table(
        "workflow",
        metadata,
        id_column(),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.String(500), server_default="", nullable=True),
        sa.Column("flow_type", sa.String(20), nullable=False, server_default="WORKFLOW"),
        sa.Column("status", sa.String(20), nullable=False, server_default="DRAFT"),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_workflow_flow_type", "flow_type"),
    )

    sa.Table(
        "workflow_node",
        metadata,
        id_column(),
        sa.Column("workflow_id", BIGINT, nullable=False),
        sa.Column("node_key", sa.String(100), nullable=False),
        sa.Column("type", sa.String(50), nullable=False),
        sa.Column("name", sa.String(100), nullable=False, server_default=""),
        sa.Column("config", sa.JSON(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_workflow_node_workflow_id", "workflow_id"),
    )

    sa.Table(
        "workflow_edge",
        metadata,
        id_column(),
        sa.Column("workflow_id", BIGINT, nullable=False),
        sa.Column("source_node_key", sa.String(100), nullable=False),
        sa.Column("target_node_key", sa.String(100), nullable=False),
        sa.Column("condition_expr", sa.String(500), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_workflow_edge_workflow_id", "workflow_id"),
    )

    sa.Table(
        "workflow_run",
        metadata,
        id_column(),
        sa.Column("workflow_id", BIGINT, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("input", sa.JSON(), nullable=True),
        sa.Column("output", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("elapsed_ms", sa.Integer, nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_workflow_run_workflow_id", "workflow_id"),
    )

    sa.Table(
        "workflow_node_run",
        metadata,
        id_column(),
        sa.Column("workflow_run_id", BIGINT, nullable=False),
        sa.Column("node_key", sa.String(100), nullable=False),
        sa.Column("node_type", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="RUNNING"),
        sa.Column("selection_state", sa.JSON(), nullable=True),
        sa.Column("inputs", sa.JSON(), nullable=True),
        sa.Column("outputs", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("elapsed_ms", sa.Integer, nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_workflow_node_run_workflow_run_id", "workflow_run_id"),
    )
    register_chatflow_state_tables(metadata)
    register_runtime_event_outbox_table(metadata)
    register_chatflow_channel_tables(metadata)
    register_workflow_publish_tables(metadata)
    register_runtime_job_tables(metadata)
    register_handoff_tables(metadata)
    register_audit_tables(metadata)
    register_agent_version_tables(metadata)
    register_agent_publish_tables(metadata)
    register_agent_memory_variable_columns(metadata)
    register_agent_prompt_optimization_tables(metadata)
    register_api_resource_tables(metadata)
    register_knowledge_vector_tables(metadata)
    register_knowledge_faq_tables(metadata)
    register_evaluation_tables(metadata)
    _register_runtime_policy_tables(metadata)
    _register_customer_assistant_tables(metadata)
    _register_ai_assistant_tables(metadata)


def ensure_pgvector_extension(bind: Engine | Connection) -> None:
    if bind.dialect.name != "postgresql":
        return
    statement = sa.text("CREATE EXTENSION IF NOT EXISTS vector")
    if isinstance(bind, Engine):
        with bind.begin() as connection:
            connection.execute(statement)
        return
    bind.execute(statement)


def tables_for_bind(bind: Engine | Connection) -> list[sa.Table]:
    if bind.dialect.name == "mysql":
        return [
            table
            for table in Base.metadata.sorted_tables
            if table.name not in RELATIONAL_VECTOR_TABLES
        ]
    return list(Base.metadata.sorted_tables)


def _register_runtime_policy_tables(metadata: sa.MetaData) -> None:
    from app.modules.runtime_policy.infra.schema import register_runtime_policy_tables

    register_runtime_policy_tables(metadata)


def _register_customer_assistant_tables(metadata: sa.MetaData) -> None:
    from app.modules.customer_assistant.infra.schema import register_customer_assistant_tables

    register_customer_assistant_tables(metadata)


def _register_ai_assistant_tables(metadata: sa.MetaData) -> None:
    from app.modules.ai_assistant.infra.schema import register_ai_assistant_tables

    register_ai_assistant_tables(metadata)


def register_chatflow_state_tables(metadata: sa.MetaData) -> None:
    if "chatflow_session" in metadata.tables:
        register_runtime_event_outbox_table(metadata)
        return

    sa.Table(
        "chatflow_session",
        metadata,
        id_column(),
        sa.Column("session_id", sa.String(120), nullable=False),
        sa.Column("chatflow_id", BIGINT, nullable=False),
        sa.Column("conversation_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("user_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("channel", sa.String(50), nullable=False, server_default="web"),
        sa.Column("channel_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="active"),
        sa.Column("current_run_id", BIGINT, nullable=True),
        sa.Column("variables", sa.JSON(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_chatflow_session_chatflow_id", "chatflow_id"),
        sa.Index("idx_chatflow_session_session_id", "session_id"),
    )

    sa.Table(
        "chatflow_event",
        metadata,
        id_column(),
        sa.Column("session_id", sa.String(120), nullable=False),
        sa.Column("chatflow_id", BIGINT, nullable=False),
        sa.Column("run_id", BIGINT, nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False, server_default="1"),
        sa.Column("event_type", sa.String(40), nullable=False),
        sa.Column("node_key", sa.String(100), nullable=False, server_default=""),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("checkpoint_id", BIGINT, nullable=True),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("run_id", "sequence", name="idx_chatflow_event_run_sequence"),
        sa.Index("idx_chatflow_event_run_id", "run_id"),
        sa.Index("idx_chatflow_event_session_id", "session_id"),
    )

    sa.Table(
        "chatflow_checkpoint",
        metadata,
        id_column(),
        sa.Column("session_id", sa.String(120), nullable=False),
        sa.Column("chatflow_id", BIGINT, nullable=False),
        sa.Column("run_id", BIGINT, nullable=False),
        sa.Column("event_id", BIGINT, nullable=True),
        sa.Column("pending_node_key", sa.String(100), nullable=False),
        sa.Column("next_edge_hint", sa.String(100), nullable=False, server_default=""),
        sa.Column("execution_context", sa.JSON(), nullable=True),
        sa.Column("node_outputs", sa.JSON(), nullable=True),
        sa.Column("variable_scopes", sa.JSON(), nullable=True),
        sa.Column("resume_schema", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=False, server_default="waiting"),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_chatflow_checkpoint_run_id", "run_id"),
        sa.Index("idx_chatflow_checkpoint_session_id", "session_id"),
    )

    register_runtime_event_outbox_table(metadata)


def register_runtime_event_outbox_table(metadata: sa.MetaData) -> None:
    if "runtime_event_outbox" in metadata.tables:
        return

    sa.Table(
        "runtime_event_outbox",
        metadata,
        id_column(),
        sa.Column("run_id", BIGINT, nullable=False),
        sa.Column("event_id", BIGINT, nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="PENDING"),
        sa.Column("attempt_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("event_id", name="idx_runtime_event_outbox_event_id"),
        sa.Index("idx_runtime_event_outbox_run_id", "run_id"),
        sa.Index("idx_runtime_event_outbox_status", "status", "updated_at"),
    )


def register_chatflow_channel_tables(metadata: sa.MetaData) -> None:
    if "chatflow_channel_config" in metadata.tables:
        return

    sa.Table(
        "chatflow_channel_config",
        metadata,
        id_column(),
        sa.Column("chatflow_id", BIGINT, nullable=False),
        sa.Column("channel_id", sa.String(50), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("config", sa.JSON(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("chatflow_id", "channel_id", name="idx_chatflow_channel_unique"),
        sa.Index("idx_chatflow_channel_chatflow_id", "chatflow_id"),
    )


def register_workflow_publish_tables(metadata: sa.MetaData) -> None:
    if "workflow_published_version" in metadata.tables:
        return

    sa.Table(
        "workflow_published_version",
        metadata,
        id_column(),
        sa.Column("workflow_id", BIGINT, nullable=False),
        sa.Column("flow_type", sa.String(20), nullable=False, server_default="WORKFLOW"),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("snapshot", sa.JSON(), nullable=False),
        sa.Column("validation", sa.JSON(), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.false()),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("workflow_id", "flow_type", "version", name="idx_workflow_version_unique"),
        sa.Index("idx_workflow_version_workflow_id", "workflow_id"),
    )


def register_runtime_job_tables(metadata: sa.MetaData) -> None:
    if "runtime_jobs" in metadata.tables:
        return

    sa.Table(
        "runtime_jobs",
        metadata,
        id_column(),
        sa.Column("run_id", BIGINT, nullable=False),
        sa.Column("owner_type", sa.String(20), nullable=False),
        sa.Column("owner_id", BIGINT, nullable=False),
        sa.Column("job_type", sa.String(60), nullable=False, server_default="runtime_v2_completion"),
        sa.Column("status", sa.String(30), nullable=False, server_default="QUEUED"),
        sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("max_attempts", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("lease_owner", sa.String(120), nullable=False, server_default=""),
        sa.Column("lease_token", sa.String(120), nullable=False, server_default=""),
        sa.Column("lease_expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_heartbeat_at", sa.DateTime(), nullable=True),
        sa.Column("available_at", sa.DateTime(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.UniqueConstraint("run_id", "job_type", name="idx_runtime_jobs_run_type"),
        sa.Index("idx_runtime_jobs_run_id", "run_id"),
        sa.Index("idx_runtime_jobs_status_available", "status", "available_at"),
        sa.Index("idx_runtime_jobs_lease_expiry", "status", "lease_expires_at"),
        sa.Index("idx_runtime_jobs_owner", "owner_type", "owner_id"),
    )


def register_handoff_tables(metadata: sa.MetaData) -> None:
    if "handoff_ticket" in metadata.tables:
        return

    sa.Table(
        "handoff_ticket",
        metadata,
        id_column(),
        sa.Column("session_id", sa.String(120), nullable=False),
        sa.Column("conversation_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("user_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("channel", sa.String(50), nullable=False, server_default="web"),
        sa.Column("queue", sa.String(120), nullable=False, server_default="general"),
        sa.Column("assignee", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="queued"),
        sa.Column("reason", sa.String(120), nullable=False, server_default=""),
        sa.Column("priority", sa.String(40), nullable=False, server_default="normal"),
        sa.Column("sla_due_at", sa.DateTime(), nullable=True),
        sa.Column("transcript_snapshot", sa.JSON(), nullable=True),
        sa.Column("context_snapshot", sa.JSON(), nullable=True),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_handoff_ticket_session_id", "session_id"),
        sa.Index("idx_handoff_ticket_status", "status"),
    )


def register_audit_tables(metadata: sa.MetaData) -> None:
    if "audit_record" in metadata.tables:
        return

    sa.Table(
        "audit_record",
        metadata,
        id_column(),
        sa.Column("actor", sa.String(120), nullable=False, server_default="system"),
        sa.Column("action", sa.String(80), nullable=False),
        sa.Column("resource_type", sa.String(80), nullable=False),
        sa.Column("resource_id", sa.String(120), nullable=False, server_default=""),
        sa.Column("status", sa.String(40), nullable=False, server_default="succeeded"),
        sa.Column("metadata", sa.JSON(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_audit_record_action", "action"),
        sa.Index("idx_audit_record_resource", "resource_type", "resource_id"),
    )


def register_knowledge_vector_tables(metadata: sa.MetaData) -> None:
    if "document_chunk" not in metadata.tables:
        sa.Table(
            "document_chunk",
            metadata,
            id_column(),
            sa.Column("document_id", BIGINT, nullable=False),
            sa.Column("chunk_index", sa.Integer(), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("content_hash", sa.String(64), nullable=False),
            sa.Column("metadata", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint(
                "document_id",
                "chunk_index",
                name="idx_document_chunk_document_chunk_index",
            ),
            sa.Index("idx_document_chunk_document_id", "document_id"),
            sa.Index("idx_document_chunk_content_hash", "content_hash"),
        )


def register_knowledge_faq_tables(metadata: sa.MetaData) -> None:
    if "knowledge_faq" not in metadata.tables:
        sa.Table(
            "knowledge_faq",
            metadata,
            id_column(),
            sa.Column("knowledge_base_id", BIGINT, nullable=False),
            sa.Column("question", sa.Text(), nullable=False),
            sa.Column("answer", sa.Text(), nullable=False),
            sa.Column("alternative_questions", sa.JSON(), nullable=True),
            sa.Column("keywords", sa.JSON(), nullable=True),
            sa.Column("category", sa.String(120), nullable=False, server_default=""),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("metadata", sa.JSON(), nullable=True),
            sa.Column("source", sa.String(80), nullable=False, server_default="manual"),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_knowledge_faq_knowledge_base_id", "knowledge_base_id"),
            sa.Index("idx_knowledge_faq_enabled", "enabled"),
        )

    if "knowledge_faq_embedding" not in metadata.tables:
        sa.Table(
            "knowledge_faq_embedding",
            metadata,
            id_column(),
            sa.Column("faq_id", BIGINT, nullable=False),
            sa.Column("embedding_model", sa.String(100), nullable=False),
            sa.Column("embedding", Vector(DEFAULT_EMBEDDING_DIMENSIONS), nullable=False),
            sa.Column(
                "dimension",
                sa.Integer(),
                nullable=False,
                server_default=str(DEFAULT_EMBEDDING_DIMENSIONS),
            ),
            sa.Column("metadata", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("faq_id", "embedding_model", name="idx_faq_embedding_faq_model"),
            sa.Index("idx_knowledge_faq_embedding_faq_id", "faq_id"),
            sa.Index(
                "idx_knowledge_faq_embedding_vector_cosine",
                "embedding",
                postgresql_using="ivfflat",
                postgresql_ops={"embedding": "vector_cosine_ops"},
                postgresql_with={"lists": 100},
            ),
        )


def register_evaluation_tables(metadata: sa.MetaData) -> None:
    if "eval_set" not in metadata.tables:
        sa.Table(
            "eval_set",
            metadata,
            id_column(),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("description", sa.String(500), server_default="", nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_eval_set_name", "name"),
        )

    if "eval_case" not in metadata.tables:
        sa.Table(
            "eval_case",
            metadata,
            id_column(),
            sa.Column("eval_set_id", BIGINT, nullable=False),
            sa.Column("input", sa.Text(), nullable=False),
            sa.Column("expected_output", sa.Text(), nullable=False),
            sa.Column("tags", sa.JSON(), nullable=True),
            sa.Column("case_metadata", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_eval_case_eval_set_id", "eval_set_id"),
        )

    if "eval_set_field" not in metadata.tables:
        sa.Table(
            "eval_set_field",
            metadata,
            id_column(),
            sa.Column("eval_set_id", BIGINT, nullable=False),
            sa.Column("key", sa.String(80), nullable=False),
            sa.Column("label", sa.String(120), nullable=False),
            sa.Column("content_type", sa.String(40), nullable=False, server_default="TEXT"),
            sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("display_order", sa.Integer(), nullable=False, server_default="0"),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("eval_set_id", "key", name="idx_eval_set_field_unique"),
            sa.Index("idx_eval_set_field_eval_set_id", "eval_set_id"),
        )

    if "eval_set_version" not in metadata.tables:
        sa.Table(
            "eval_set_version",
            metadata,
            id_column(),
            sa.Column("eval_set_id", BIGINT, nullable=False),
            sa.Column("version", sa.String(40), nullable=False),
            sa.Column("schema_snapshot", sa.JSON(), nullable=False),
            sa.Column("case_snapshot", sa.JSON(), nullable=False),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("created_by", sa.String(120), nullable=False, server_default="system"),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("eval_set_id", "version", name="idx_eval_set_version_unique"),
            sa.Index("idx_eval_set_version_eval_set_id", "eval_set_id"),
        )

    if "evaluator" not in metadata.tables:
        sa.Table(
            "evaluator",
            metadata,
            id_column(),
            sa.Column("name", sa.String(120), nullable=False),
            sa.Column("type", sa.String(40), nullable=False),
            sa.Column("config", sa.JSON(), nullable=True),
            enabled_column(),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_evaluator_type", "type"),
        )

    if "evaluator_version" not in metadata.tables:
        sa.Table(
            "evaluator_version",
            metadata,
            id_column(),
            sa.Column("evaluator_id", BIGINT, nullable=False),
            sa.Column("version", sa.String(40), nullable=False),
            sa.Column("evaluator_type", sa.String(40), nullable=False),
            sa.Column("config_snapshot", sa.JSON(), nullable=False),
            sa.Column("input_schema", sa.JSON(), nullable=False),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("evaluator_id", "version", name="idx_evaluator_version_unique"),
            sa.Index("idx_evaluator_version_evaluator_id", "evaluator_id"),
        )

    if "evaluation_experiment" not in metadata.tables:
        sa.Table(
            "evaluation_experiment",
            metadata,
            id_column(),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("target_type", sa.String(40), nullable=False),
            sa.Column("target_id", BIGINT, nullable=False),
            sa.Column("eval_set_id", BIGINT, nullable=False),
            sa.Column("eval_set_version_id", BIGINT, nullable=True),
            sa.Column("evaluator_ids", sa.JSON(), nullable=False),
            sa.Column("evaluator_version_ids", sa.JSON(), nullable=True),
            sa.Column("target_field_mapping", sa.JSON(), nullable=True),
            sa.Column("evaluator_field_mapping", sa.JSON(), nullable=True),
            sa.Column("item_concurrency", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("item_retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("status", sa.String(30), nullable=False, server_default="READY"),
            sa.Column("latest_run_id", BIGINT, nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_evaluation_experiment_target", "target_type", "target_id"),
            sa.Index("idx_evaluation_experiment_eval_set", "eval_set_id", "eval_set_version_id"),
        )

    if "evaluation_run" not in metadata.tables:
        sa.Table(
            "evaluation_run",
            metadata,
            id_column(),
            sa.Column("experiment_id", BIGINT, nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="RUNNING"),
            sa.Column("total_cases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("passed_cases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("failed_cases", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("aggregate_score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("pass_rate", sa.Float(), nullable=False, server_default="0"),
            sa.Column("started_at", sa.DateTime(), nullable=True),
            sa.Column("finished_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_evaluation_run_experiment_id", "experiment_id"),
        )

    if "evaluation_case_result" not in metadata.tables:
        sa.Table(
            "evaluation_case_result",
            metadata,
            id_column(),
            sa.Column("run_id", BIGINT, nullable=False),
            sa.Column("eval_case_id", BIGINT, nullable=False),
            sa.Column("input", sa.Text(), nullable=False),
            sa.Column("expected_output", sa.Text(), nullable=False),
            sa.Column("target_output", sa.Text(), nullable=False),
            sa.Column("target_type", sa.String(30), nullable=True),
            sa.Column("target_run_id", BIGINT, nullable=True),
            sa.Column("target_status", sa.String(30), nullable=True),
            sa.Column("target_debug_url", sa.String(500), nullable=True),
            sa.Column("target_evidence_summary", sa.JSON(), nullable=True),
            sa.Column("status", sa.String(30), nullable=False),
            sa.Column("score", sa.Float(), nullable=False, server_default="0"),
            sa.Column("evaluator_results", sa.JSON(), nullable=True),
            sa.Column("reason", sa.Text(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_evaluation_case_result_run_id", "run_id"),
        )

    if "document_embedding" not in metadata.tables:
        sa.Table(
            "document_embedding",
            metadata,
            id_column(),
            sa.Column("chunk_id", BIGINT, nullable=False),
            sa.Column("embedding_model", sa.String(100), nullable=False),
            sa.Column("embedding", Vector(DEFAULT_EMBEDDING_DIMENSIONS), nullable=False),
            sa.Column(
                "dimension",
                sa.Integer(),
                nullable=False,
                server_default=str(DEFAULT_EMBEDDING_DIMENSIONS),
            ),
            sa.Column("metadata", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("chunk_id", "embedding_model", name="idx_embedding_chunk_model"),
            sa.Index("idx_document_embedding_chunk_id", "chunk_id"),
            sa.Index(
                "idx_document_embedding_vector_cosine",
                "embedding",
                postgresql_using="ivfflat",
                postgresql_ops={"embedding": "vector_cosine_ops"},
                postgresql_with={"lists": 100},
            ),
        )


def register_agent_version_tables(metadata: sa.MetaData) -> None:
    if "agent_version" not in metadata.tables:
        sa.Table(
            "agent_version",
            metadata,
            id_column(),
            sa.Column("agent_id", BIGINT, nullable=False),
            sa.Column("version_no", sa.Integer(), nullable=False),
            sa.Column("name", sa.String(160), nullable=False, server_default=""),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            sa.Column("released", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("released_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("agent_id", "version_no", name="idx_agent_version_agent_no"),
            sa.Index("idx_agent_version_agent_id", "agent_id"),
        )


def register_agent_publish_tables(metadata: sa.MetaData) -> None:
    if "agent_publish_record" not in metadata.tables:
        sa.Table(
            "agent_publish_record",
            metadata,
            id_column(),
            sa.Column("agent_id", BIGINT, nullable=False),
            sa.Column("version_id", BIGINT, nullable=False),
            sa.Column("channel_type", sa.String(40), nullable=False),
            sa.Column("status", sa.String(40), nullable=False, server_default="PUBLISHED"),
            sa.Column("endpoint", sa.String(500), nullable=False, server_default=""),
            sa.Column("config", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_agent_publish_agent_id", "agent_id"),
            sa.Index("idx_agent_publish_version_id", "version_id"),
        )


def register_agent_memory_variable_columns(metadata: sa.MetaData) -> None:
    agent = metadata.tables.get("agent")
    if agent is None:
        return
    if "variables" not in agent.c:
        agent.append_column(sa.Column("variables", sa.JSON(), nullable=True))
    if "memory" not in agent.c:
        agent.append_column(sa.Column("memory", sa.JSON(), nullable=True))
    if "tool_policies" not in agent.c:
        agent.append_column(sa.Column("tool_policies", sa.JSON(), nullable=True))
    if "knowledge_base_ids" not in agent.c:
        agent.append_column(sa.Column("knowledge_base_ids", sa.JSON(), nullable=True))
    if "retrieval_settings" not in agent.c:
        agent.append_column(sa.Column("retrieval_settings", sa.JSON(), nullable=True))
    if "evaluation_gate" not in agent.c:
        agent.append_column(sa.Column("evaluation_gate", sa.JSON(), nullable=True))
    for column_name in ("access", "sharing", "catalog", "analytics"):
        if column_name not in agent.c:
            agent.append_column(sa.Column(column_name, sa.JSON(), nullable=True))


def register_agent_prompt_optimization_tables(metadata: sa.MetaData) -> None:
    if "agent_prompt_optimization" not in metadata.tables:
        sa.Table(
            "agent_prompt_optimization",
            metadata,
            id_column(),
            sa.Column("agent_id", BIGINT, nullable=False),
            sa.Column("original_prompt", sa.Text(), nullable=False),
            sa.Column("instruction", sa.Text(), nullable=False),
            sa.Column("optimized_prompt", sa.Text(), nullable=False),
            sa.Column("model_config_id", BIGINT, nullable=False),
            sa.Column("audit", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_agent_prompt_optimization_agent_id", "agent_id"),
        )


def register_api_resource_tables(metadata: sa.MetaData) -> None:
    if "api_resource" not in metadata.tables:
        sa.Table(
            "api_resource",
            metadata,
            id_column(),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("method", sa.String(16), nullable=False, server_default="GET"),
            sa.Column("endpoint", sa.String(1000), nullable=False),
            sa.Column("auth_mode", sa.String(40), nullable=False, server_default="none"),
            sa.Column("headers", sa.JSON(), nullable=True),
            sa.Column("body_template", sa.Text(), nullable=False),
            sa.Column("input_schema", sa.JSON(), nullable=True),
            sa.Column("output_schema", sa.JSON(), nullable=True),
            sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="30000"),
            sa.Column("test_payload", sa.JSON(), nullable=True),
            enabled_column(),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_api_resource_name", "name"),
        )

    if "api_tool" not in metadata.tables:
        sa.Table(
            "api_tool",
            metadata,
            id_column(),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("display_name", sa.String(160), nullable=False, server_default=""),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("adapter_type", sa.String(40), nullable=False, server_default="API_RESOURCE"),
            sa.Column("api_resource_id", BIGINT, nullable=True),
            sa.Column("input_schema", sa.JSON(), nullable=True),
            sa.Column("output_schema", sa.JSON(), nullable=True),
            sa.Column("model_callable", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("timeout_ms", sa.Integer(), nullable=False, server_default="30000"),
            sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("error_behavior", sa.String(20), nullable=False, server_default="fail"),
            enabled_column(),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_api_tool_name", "name"),
            sa.Index("idx_api_tool_resource_id", "api_resource_id"),
        )


def id_column() -> sa.Column[int]:
    return sa.Column("id", BIGINT, primary_key=True, autoincrement=True)


def enabled_column() -> sa.Column[bool]:
    return sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.true())


def deleted_column() -> sa.Column[bool]:
    return sa.Column("deleted", sa.Boolean(), nullable=False, server_default=sa.false())


def timestamps() -> tuple[sa.Column[Any], sa.Column[Any]]:
    return (
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
