from sqlalchemy.orm import sessionmaker

from app.modules.ai_assistant.domain.access_scope import local_ai_assistant_scope
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.event_stream_reader import (
    AiAssistantRunEventStreamReader,
)
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from tests.support.mysql import mysql8_session


def test_sse_reader_releases_database_connection_between_polls() -> None:
    with mysql8_session("ai_assistant_sse_short_sessions") as session:
        repository = AiAssistantRepository(session)
        service = AiAssistantHarnessService(repository)
        assistant_session = service.create_session(title="Short SSE sessions")
        started = service.run_message(
            int(assistant_session["id"]),
            "stream from short sessions",
            idempotency_key="sse-short-session",
        )
        run_id = int(started.run["id"])
        bind = session.get_bind()
        session.close()
        baseline = bind.pool.checkedout()
        reader = AiAssistantRunEventStreamReader(
            sessionmaker(
                bind=bind,
                autoflush=False,
                autocommit=False,
                expire_on_commit=False,
            ),
            access_scope=local_ai_assistant_scope(),
        )

        first = reader.read(run_id, after_sequence=0)
        second = reader.read(
            run_id,
            after_sequence=int(first.events[-1]["sequence"]),
        )

        assert first.run["status"] == "COMPLETED"
        assert first.events
        assert second.events == []
        assert bind.pool.checkedout() == baseline
