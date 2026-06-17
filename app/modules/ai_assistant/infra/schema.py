import sqlalchemy as sa

from app.core.database import Base
from app.core.schema import deleted_column, id_column, timestamps


BIGINT = sa.BigInteger()


def register_ai_assistant_tables(metadata: sa.MetaData | None = None) -> None:
    target = metadata or Base.metadata
    if "ai_assistant_session" not in target.tables:
        sa.Table(
            "ai_assistant_session",
            target,
            id_column(),
            sa.Column("title", sa.String(200), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            sa.Column("context_json", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_ai_assistant_session_status", "status"),
        )

    if "ai_assistant_run" not in target.tables:
        sa.Table(
            "ai_assistant_run",
            target,
            id_column(),
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


def ai_assistant_tables() -> list[sa.Table]:
    register_ai_assistant_tables()
    names = [
        "ai_assistant_session",
        "ai_assistant_run",
        "ai_assistant_message",
        "ai_assistant_event",
        "ai_assistant_tool_call",
    ]
    return [Base.metadata.tables[name] for name in names]
