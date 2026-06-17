from collections.abc import Generator

import sqlalchemy as sa
from sqlalchemy import MetaData, create_engine
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.engine.reflection import Inspector
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import get_settings
from app.core.database_url_policy import assert_mysql8_connection, assert_mysql8_database_url


NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)


def make_engine(database_url: str, echo: bool = False) -> Engine:
    assert_mysql8_database_url(database_url)
    engine = create_engine(database_url, echo=echo, future=True)
    assert_mysql8_connection(engine)
    return engine


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def get_engine() -> Engine:
    return make_engine(get_settings().database_url)


def get_session_factory() -> sessionmaker[Session]:
    return make_session_factory(get_engine())


def initialise_database() -> None:
    from app.core.schema import ensure_pgvector_extension, register_baseline_tables, tables_for_bind

    register_baseline_tables()
    engine = get_engine()
    ensure_pgvector_extension(engine)
    Base.metadata.create_all(bind=engine, tables=tables_for_bind(engine))
    _ensure_compatible_schema(engine)


def check_database_schema(engine: Engine | None = None) -> None:
    from app.core.schema import register_baseline_tables, tables_for_bind

    register_baseline_tables()
    target_engine = engine or get_engine()
    inspector = sa.inspect(target_engine)
    table_names = set(inspector.get_table_names())
    expected_tables = tables_for_bind(target_engine)
    missing_tables = sorted(table.name for table in expected_tables if table.name not in table_names)
    missing_columns: list[str] = []
    for table in expected_tables:
        if table.name in missing_tables:
            continue
        actual_columns = {column["name"] for column in inspector.get_columns(table.name)}
        for column in table.columns:
            if column.name not in actual_columns:
                missing_columns.append(f"{table.name}.{column.name}")
    if not missing_tables and not missing_columns:
        return
    details: list[str] = []
    if missing_tables:
        details.append(f"missing tables: {', '.join(missing_tables)}")
    if missing_columns:
        details.append(f"missing columns: {', '.join(sorted(missing_columns))}")
    raise RuntimeError(f"Database schema check failed: {'; '.join(details)}")


def _ensure_compatible_schema(engine: Engine) -> None:
    inspector = sa.inspect(engine)
    table_names = inspector.get_table_names()
    if "workflow" not in table_names:
        return

    workflow_columns = {column["name"] for column in inspector.get_columns("workflow")}
    agent_columns = {column["name"] for column in inspector.get_columns("agent")} if "agent" in table_names else set()
    chatflow_session_columns = (
        {column["name"] for column in inspector.get_columns("chatflow_session")}
        if "chatflow_session" in table_names
        else set()
    )
    chatflow_event_indexes = (
        {index["name"] for index in inspector.get_indexes("chatflow_event")}
        if "chatflow_event" in table_names
        else set()
    )
    chat_message_columns = (
        {column["name"] for column in inspector.get_columns("chat_message")}
        if "chat_message" in table_names
        else set()
    )
    experiment_columns = (
        {column["name"] for column in inspector.get_columns("evaluation_experiment")}
        if "evaluation_experiment" in table_names
        else set()
    )
    case_result_columns = (
        {column["name"] for column in inspector.get_columns("evaluation_case_result")}
        if "evaluation_case_result" in table_names
        else set()
    )
    customer_assistant_event_columns = (
        {column["name"] for column in inspector.get_columns("customer_assistant_event")}
        if "customer_assistant_event" in table_names
        else set()
    )

    with engine.begin() as connection:
        if "flow_type" not in workflow_columns:
            connection.execute(
                sa.text("ALTER TABLE workflow ADD COLUMN flow_type VARCHAR(20) NOT NULL DEFAULT 'WORKFLOW'")
            )
            _create_index_if_missing(connection, inspector, "workflow", "idx_workflow_flow_type", "flow_type")
        if "agent" in table_names and "opening_message" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN opening_message TEXT"))
        if "agent" in table_names and "suggested_questions" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN suggested_questions JSON"))
        if "agent" in table_names and "variables" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN variables JSON"))
        if "agent" in table_names and "memory" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN memory JSON"))
        if "agent" in table_names and "tool_policies" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN tool_policies JSON"))
        if "agent" in table_names and "knowledge_base_ids" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN knowledge_base_ids JSON"))
        if "agent" in table_names and "retrieval_settings" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN retrieval_settings JSON"))
        if "agent" in table_names and "evaluation_gate" not in agent_columns:
            connection.execute(sa.text("ALTER TABLE agent ADD COLUMN evaluation_gate JSON"))
        for column_name in ("access", "sharing", "catalog", "analytics"):
            if "agent" in table_names and column_name not in agent_columns:
                connection.execute(sa.text(f"ALTER TABLE agent ADD COLUMN {column_name} JSON"))
        if "chatflow_session" in table_names and "variables" not in chatflow_session_columns:
            connection.execute(sa.text("ALTER TABLE chatflow_session ADD COLUMN variables JSON"))
        if (
            "chatflow_event" in table_names
            and "idx_chatflow_event_run_sequence" not in chatflow_event_indexes
            and not _has_chatflow_event_sequence_duplicates(connection)
        ):
            connection.execute(
                sa.text("CREATE UNIQUE INDEX idx_chatflow_event_run_sequence ON chatflow_event (run_id, sequence)")
            )
        if "chat_message" in table_names and "tool_calls" not in chat_message_columns:
            connection.execute(sa.text("ALTER TABLE chat_message ADD COLUMN tool_calls JSON"))
        if "evaluation_experiment" in table_names and "eval_set_version_id" not in experiment_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_experiment ADD COLUMN eval_set_version_id BIGINT"))
            _create_index_if_missing(
                connection,
                inspector,
                "evaluation_experiment",
                "idx_evaluation_experiment_eval_set",
                "eval_set_id, eval_set_version_id",
            )
        if "evaluation_experiment" in table_names and "target_field_mapping" not in experiment_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_experiment ADD COLUMN target_field_mapping JSON"))
        if "evaluation_experiment" in table_names and "evaluator_field_mapping" not in experiment_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_experiment ADD COLUMN evaluator_field_mapping JSON"))
        if "evaluation_experiment" in table_names and "evaluator_version_ids" not in experiment_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_experiment ADD COLUMN evaluator_version_ids JSON"))
        if "evaluation_experiment" in table_names and "item_concurrency" not in experiment_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_experiment ADD COLUMN item_concurrency INTEGER NOT NULL DEFAULT 1"))
        if "evaluation_experiment" in table_names and "item_retry_count" not in experiment_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_experiment ADD COLUMN item_retry_count INTEGER NOT NULL DEFAULT 0"))
        if "evaluation_case_result" in table_names and "target_type" not in case_result_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_case_result ADD COLUMN target_type VARCHAR(30)"))
        if "evaluation_case_result" in table_names and "target_run_id" not in case_result_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_case_result ADD COLUMN target_run_id BIGINT"))
        if "evaluation_case_result" in table_names and "target_status" not in case_result_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_case_result ADD COLUMN target_status VARCHAR(30)"))
        if "evaluation_case_result" in table_names and "target_debug_url" not in case_result_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_case_result ADD COLUMN target_debug_url VARCHAR(500)"))
        if "evaluation_case_result" in table_names and "target_evidence_summary" not in case_result_columns:
            connection.execute(sa.text("ALTER TABLE evaluation_case_result ADD COLUMN target_evidence_summary JSON"))
        if "customer_assistant_event" in table_names and "actor" not in customer_assistant_event_columns:
            connection.execute(
                sa.text(
                    "ALTER TABLE customer_assistant_event "
                    "ADD COLUMN actor VARCHAR(30) NOT NULL DEFAULT 'customer'"
                )
            )


def _create_index_if_missing(
    connection: Connection,
    inspector: Inspector,
    table_name: str,
    index_name: str,
    column_sql: str,
) -> None:
    existing = {index["name"] for index in inspector.get_indexes(table_name)}
    if index_name in existing:
        return
    connection.execute(sa.text(f"CREATE INDEX {index_name} ON {table_name} ({column_sql})"))


def _has_chatflow_event_sequence_duplicates(connection: Connection) -> bool:
    duplicate = connection.execute(
        sa.text(
            """
            SELECT 1
            FROM chatflow_event
            GROUP BY run_id, sequence
            HAVING COUNT(*) > 1
            LIMIT 1
            """
        )
    ).first()
    return duplicate is not None


def get_session() -> Generator[Session]:
    with get_session_factory()() as session:
        yield session
