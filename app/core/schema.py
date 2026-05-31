from typing import Any

from pgvector.sqlalchemy import Vector  # type: ignore[import-untyped]
import sqlalchemy as sa
from sqlalchemy.engine import Connection, Engine

from app.core.database import Base

BIGINT = sa.BigInteger().with_variant(sa.Integer, "sqlite")
DEFAULT_EMBEDDING_DIMENSIONS = 1536


def register_baseline_tables() -> None:
    metadata = Base.metadata
    if "provider" in metadata.tables:
        register_knowledge_vector_tables(metadata)
        register_evaluation_tables(metadata)
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
        sa.Column("system_prompt", sa.Text(), server_default="", nullable=True),
        sa.Column("model_config_id", BIGINT, nullable=False),
        sa.Column("temperature", sa.Numeric(3, 2), nullable=False, server_default="0.70"),
        sa.Column("max_tokens", sa.Integer, nullable=False, server_default="2048"),
        sa.Column("max_context_turns", sa.Integer, nullable=False, server_default="10"),
        enabled_column(),
        sa.Column("knowledge_base_id", BIGINT, nullable=True),
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
        sa.Column("config", sa.JSON(), server_default="{}", nullable=True),
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
        sa.Column("outputs", sa.JSON(), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("elapsed_ms", sa.Integer, nullable=True),
        sa.Column("finished_at", sa.DateTime(), nullable=True),
        deleted_column(),
        *timestamps(),
        sa.Index("idx_workflow_node_run_workflow_run_id", "workflow_run_id"),
    )
    register_knowledge_vector_tables(metadata)
    register_evaluation_tables(metadata)


def ensure_pgvector_extension(bind: Engine | Connection) -> None:
    if bind.dialect.name != "postgresql":
        return
    statement = sa.text("CREATE EXTENSION IF NOT EXISTS vector")
    if isinstance(bind, Engine):
        with bind.begin() as connection:
            connection.execute(statement)
        return
    bind.execute(statement)


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

    if "evaluation_experiment" not in metadata.tables:
        sa.Table(
            "evaluation_experiment",
            metadata,
            id_column(),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("target_type", sa.String(40), nullable=False),
            sa.Column("target_id", BIGINT, nullable=False),
            sa.Column("eval_set_id", BIGINT, nullable=False),
            sa.Column("evaluator_ids", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="READY"),
            sa.Column("latest_run_id", BIGINT, nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_evaluation_experiment_target", "target_type", "target_id"),
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
