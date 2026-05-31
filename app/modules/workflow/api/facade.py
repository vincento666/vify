from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.workflow.domain.engine import WorkflowExecutionEngine, WorkflowLlmCompleter
from app.modules.workflow.infra.repository import WorkflowRepository


class WorkflowFacade:
    def __init__(self, session: Session) -> None:
        self._repository = WorkflowRepository(session)
        self._knowledge_facade = KnowledgeFacade(session)
        self._engine = WorkflowExecutionEngine(self._repository, self._knowledge_facade)

    def execute_for_chat(
        self,
        workflow_id: int,
        user_message: str,
        llm_completer: WorkflowLlmCompleter | None = None,
    ) -> str | None:
        if not self._repository.list_nodes(workflow_id):
            return None
        engine = (
            self._engine
            if llm_completer is None
            else WorkflowExecutionEngine(self._repository, self._knowledge_facade, llm_completer)
        )
        result = engine.run(workflow_id, {"userMessage": user_message})
        return _string_output(result.output)


def _string_output(output: dict[str, Any]) -> str:
    if "answer" in output:
        return str(output["answer"])
    if "output" in output:
        return str(output["output"])
    if len(output) == 1:
        return str(next(iter(output.values())))
    return str(output)
