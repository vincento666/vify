import sqlalchemy as sa

from app.core.database import _ensure_compatible_schema


def test_compatible_schema_skips_chatflow_event_unique_index_when_legacy_duplicates_exist() -> None:
    engine = sa.create_engine("sqlite:///:memory:", future=True)
    with engine.begin() as connection:
        connection.execute(sa.text("CREATE TABLE workflow (id INTEGER PRIMARY KEY, name VARCHAR(100))"))
        connection.execute(
            sa.text(
                """
                CREATE TABLE chatflow_event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id VARCHAR(120) NOT NULL,
                    chatflow_id BIGINT NOT NULL,
                    run_id BIGINT NOT NULL,
                    sequence INTEGER NOT NULL,
                    event_type VARCHAR(40) NOT NULL,
                    node_key VARCHAR(100) NOT NULL,
                    payload JSON,
                    checkpoint_id BIGINT,
                    deleted BOOLEAN NOT NULL DEFAULT 0,
                    created_at DATETIME NOT NULL,
                    updated_at DATETIME NOT NULL
                )
                """
            )
        )
        for event_id in (1, 2):
            connection.execute(
                sa.text(
                    """
                    INSERT INTO chatflow_event (
                        id, session_id, chatflow_id, run_id, sequence,
                        event_type, node_key, created_at, updated_at
                    )
                    VALUES (:event_id, 'legacy-session', 1, 99, 1, 'NODE_BLOCKED', 'collect', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                    """
                ),
                {"event_id": event_id},
            )

    _ensure_compatible_schema(engine)

    index_names = {index["name"] for index in sa.inspect(engine).get_indexes("chatflow_event")}
    assert "idx_chatflow_event_run_sequence" not in index_names
