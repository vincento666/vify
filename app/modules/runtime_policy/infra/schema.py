import sqlalchemy as sa

from app.core.database import Base
from app.core.schema import BIGINT, deleted_column, id_column, timestamps


def register_runtime_policy_tables(metadata: sa.MetaData | None = None) -> None:
    target = metadata or Base.metadata
    if "runtime_policy_profile" not in target.tables:
        sa.Table(
            "runtime_policy_profile",
            target,
            id_column(),
            sa.Column("name", sa.String(160), nullable=False),
            sa.Column("description", sa.String(500), nullable=False, server_default=""),
            sa.Column("status", sa.String(30), nullable=False, server_default="draft"),
            sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
            sa.Column("mode", sa.String(30), nullable=False, server_default="balanced"),
            sa.Column("bindings", sa.JSON(), nullable=False),
            sa.Column("thresholds", sa.JSON(), nullable=False),
            sa.Column("classifier", sa.JSON(), nullable=False),
            sa.Column("faq", sa.JSON(), nullable=False),
            sa.Column("rag", sa.JSON(), nullable=False),
            sa.Column("fallback_agent", sa.JSON(), nullable=False),
            sa.Column("handoff", sa.JSON(), nullable=False),
            sa.Column("audit", sa.JSON(), nullable=False),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_runtime_policy_profile_status", "status"),
            sa.Index("idx_runtime_policy_profile_mode", "mode"),
        )

    if "runtime_decision_log" not in target.tables:
        sa.Table(
            "runtime_decision_log",
            target,
            id_column(),
            sa.Column("session_id", BIGINT, nullable=False),
            sa.Column("message_id", sa.String(160), nullable=False, server_default=""),
            sa.Column("user_message", sa.Text(), nullable=False),
            sa.Column("active_task_snapshot", sa.JSON(), nullable=True),
            sa.Column("suspended_task_snapshot", sa.JSON(), nullable=True),
            sa.Column("policy_profile_id", BIGINT, nullable=True),
            sa.Column("policy_profile_version", sa.Integer(), nullable=True),
            sa.Column("policy_snapshot", sa.JSON(), nullable=False),
            sa.Column("candidate_scores", sa.JSON(), nullable=True),
            sa.Column("faq_score", sa.Float(), nullable=True),
            sa.Column("faq_margin", sa.Float(), nullable=True),
            sa.Column("semantic_score", sa.Float(), nullable=True),
            sa.Column("semantic_margin", sa.Float(), nullable=True),
            sa.Column("rag_score", sa.Float(), nullable=True),
            sa.Column("rag_lexical_overlap", sa.Float(), nullable=True),
            sa.Column("classifier_confidence", sa.Float(), nullable=True),
            sa.Column("agent_confidence", sa.Float(), nullable=True),
            sa.Column("final_action", sa.String(80), nullable=False, server_default=""),
            sa.Column("source_layer", sa.String(80), nullable=False, server_default=""),
            sa.Column("reason_code", sa.String(120), nullable=False, server_default=""),
            sa.Column("mutates_sop_state", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("handoff_triggered", sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column("route_evidence", sa.JSON(), nullable=False),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_runtime_decision_log_session", "session_id"),
            sa.Index("idx_runtime_decision_log_profile", "policy_profile_id", "policy_profile_version"),
            sa.Index("idx_runtime_decision_log_action", "final_action"),
            sa.Index("idx_runtime_decision_log_source", "source_layer"),
            sa.Index("idx_runtime_decision_log_created", "created_at"),
        )

    if "runtime_policy_evaluation_run" not in target.tables:
        sa.Table(
            "runtime_policy_evaluation_run",
            target,
            id_column(),
            sa.Column("profile_id", BIGINT, nullable=False),
            sa.Column("profile_version", sa.Integer(), nullable=False),
            sa.Column("run_type", sa.String(60), nullable=False),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("input_snapshot", sa.JSON(), nullable=False),
            sa.Column("result", sa.JSON(), nullable=False),
            sa.Column("metrics", sa.JSON(), nullable=False),
            sa.Column("risk_deltas", sa.JSON(), nullable=False),
            sa.Column("failure_reasons", sa.JSON(), nullable=False),
            sa.Column("guardrails", sa.JSON(), nullable=False),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_runtime_policy_eval_profile", "profile_id", "profile_version"),
            sa.Index("idx_runtime_policy_eval_type", "run_type"),
            sa.Index("idx_runtime_policy_eval_status", "status"),
        )

    if "runtime_policy_release" not in target.tables:
        sa.Table(
            "runtime_policy_release",
            target,
            id_column(),
            sa.Column("profile_id", BIGINT, nullable=False),
            sa.Column("profile_version", sa.Integer(), nullable=False),
            sa.Column("previous_active_profile_id", BIGINT, nullable=True),
            sa.Column("previous_active_profile_version", sa.Integer(), nullable=True),
            sa.Column("evaluation_run_ids", sa.JSON(), nullable=False),
            sa.Column("status", sa.String(40), nullable=False),
            sa.Column("canary_percent", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("approved_by", sa.String(120), nullable=False, server_default=""),
            sa.Column("activated_by", sa.String(120), nullable=False, server_default=""),
            sa.Column("rolled_back_by", sa.String(120), nullable=False, server_default=""),
            sa.Column("activated_at", sa.DateTime(), nullable=True),
            sa.Column("rolled_back_at", sa.DateTime(), nullable=True),
            sa.Column("rollback_reason", sa.String(500), nullable=False, server_default=""),
            sa.Column("audit_snapshot", sa.JSON(), nullable=False),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_runtime_policy_release_profile", "profile_id", "profile_version"),
            sa.Index("idx_runtime_policy_release_status", "status"),
        )

    if "runtime_policy_audit_event" not in target.tables:
        sa.Table(
            "runtime_policy_audit_event",
            target,
            id_column(),
            sa.Column("release_id", BIGINT, nullable=True),
            sa.Column("evaluation_run_id", BIGINT, nullable=True),
            sa.Column("profile_id", BIGINT, nullable=True),
            sa.Column("profile_version", sa.Integer(), nullable=True),
            sa.Column("event_type", sa.String(80), nullable=False),
            sa.Column("actor", sa.String(120), nullable=False, server_default=""),
            sa.Column("reason", sa.String(500), nullable=False, server_default=""),
            sa.Column("snapshot", sa.JSON(), nullable=False),
            deleted_column(),
            *timestamps(),
            sa.Index("idx_runtime_policy_audit_release", "release_id"),
            sa.Index("idx_runtime_policy_audit_eval", "evaluation_run_id"),
            sa.Index("idx_runtime_policy_audit_profile", "profile_id", "profile_version"),
            sa.Index("idx_runtime_policy_audit_type", "event_type"),
        )


def runtime_policy_tables() -> list[sa.Table]:
    register_runtime_policy_tables()
    names = [
        "runtime_policy_profile",
        "runtime_decision_log",
        "runtime_policy_evaluation_run",
        "runtime_policy_release",
        "runtime_policy_audit_event",
    ]
    return [Base.metadata.tables[name] for name in names]
