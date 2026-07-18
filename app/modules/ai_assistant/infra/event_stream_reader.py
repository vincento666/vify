from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session, sessionmaker

from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope
from app.modules.ai_assistant.infra.repository import AiAssistantRepository


@dataclass(frozen=True)
class AiAssistantEventStreamPage:
    run: dict[str, Any]
    events: list[dict[str, Any]]


class AiAssistantRunEventStreamReader:
    def __init__(
        self,
        session_factory: sessionmaker[Session],
        *,
        access_scope: AiAssistantAccessScope,
    ) -> None:
        self._session_factory = session_factory
        self._access_scope = access_scope

    def read(
        self,
        run_id: int,
        *,
        after_sequence: int,
    ) -> AiAssistantEventStreamPage:
        with self._session_factory() as session:
            repository = AiAssistantRepository(
                session,
                access_scope=self._access_scope,
            )
            run = repository.get_run(run_id)
            if run is None:
                raise KeyError(f"AI Assistant run not found: {run_id}")
            events = repository.list_run_events(
                run_id,
                after_sequence=after_sequence,
            )
            return AiAssistantEventStreamPage(run=run, events=events)
