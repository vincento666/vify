from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.workflow.domain.engine import WorkflowExecutionEngine
from app.modules.workflow.infra.repository import WorkflowRepository


class WorkflowFacade:
    def __init__(self, session: Session) -> None:
        self._repository = WorkflowRepository(session)
        self._engine = WorkflowExecutionEngine(self._repository, KnowledgeFacade(session))

    def execute_for_chat(self, workflow_id: int, user_message: str) -> str | None:
        if not self._repository.list_nodes(workflow_id):
            return None
        result = self._engine.run(workflow_id, {"userMessage": user_message})
        return _string_output(result.output)


def _string_output(output: dict[str, Any]) -> str:
    if "answer" in output:
        return str(output["answer"])
    if "output" in output:
        return str(output["output"])
    if len(output) == 1:
        return str(next(iter(output.values())))
    return str(output)
