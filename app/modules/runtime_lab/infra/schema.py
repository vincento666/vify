import sqlalchemy as sa

from app.core.database import Base
from app.core.schema import BIGINT, deleted_column, id_column, timestamps


def register_runtime_lab_tables(metadata: sa.MetaData | None = None) -> None:
    target = metadata or Base.metadata
    if "runtime_lab_session" not in target.tables:
        sa.Table(
            "runtime_lab_session",
            target,
            id_column(),
            sa.Column("status", sa.String(30), nullable=False, server_default="ACTIVE"),
            sa.Column("active_task_id", BIGINT, nullable=True),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            deleted_column(),
            *timestamps(),
        )

    if "runtime_lab_task" not in target.tables:
        sa.Table(
            "runtime_lab_task",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("sop_id", sa.String(80), nullable=False),
            sa.Column("status", sa.String(30), nullable=False, server_default="RUNNING"),
            sa.Column("parent_task_id", BIGINT, nullable=True),
            sa.Column("resume_summary", sa.Text(), nullable=False),
            sa.Column("chatflow_id", BIGINT, nullable=True),
            sa.Column("chatflow_session_id", BIGINT, nullable=True),
            sa.Column("chatflow_run_id", BIGINT, nullable=True),
            sa.Column("chatflow_event_id", BIGINT, nullable=True),
            sa.Column("chatflow_checkpoint_id", BIGINT, nullable=True),
            sa.Column("runtime_version", sa.String(20), nullable=True),
            sa.Column("suspended_at", sa.DateTime(), nullable=True),
            sa.Column("completed_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_runtime_lab_task_session", "session_id"),
            sa.Index("idx_runtime_lab_task_status", "session_id", "status"),
        )

    if "runtime_lab_event" not in target.tables:
        sa.Table(
            "runtime_lab_event",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("sequence", sa.Integer(), nullable=False),
            sa.Column("event_type", sa.String(60), nullable=False),
            sa.Column("payload", sa.JSON(), nullable=True),
            deleted_column(),
            *timestamps(),
            sa.UniqueConstraint("session_id", "sequence", name="idx_runtime_lab_event_sequence"),
            sa.Index("idx_runtime_lab_event_session", "session_id"),
        )

    if "runtime_lab_command" not in target.tables:
        sa.Table(
            "runtime_lab_command",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("idempotency_key", sa.String(160), nullable=False),
            sa.Column("request_hash", sa.String(128), nullable=False),
            sa.Column("response_payload", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.UniqueConstraint(
                "session_id",
                "idempotency_key",
                name="idx_runtime_lab_command_idempotency",
            ),
            sa.Index("idx_runtime_lab_command_session", "session_id"),
        )


def runtime_lab_tables() -> list[sa.Table]:
    register_runtime_lab_tables()
    names = [
        "runtime_lab_session",
        "runtime_lab_task",
        "runtime_lab_event",
        "runtime_lab_command",
    ]
    return [Base.metadata.tables[name] for name in names]
