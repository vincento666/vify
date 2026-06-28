"""Business context aggregator for runtime-lab sessions.

Replaces RuntimeLabService._session_business_context. Walks the runtime tasks
of a session and asks each task's child-chatflow runtime for the
`conversation` scope variables. Falls back to ``task.business_refs`` so
regex-derived slots (extracted by SOP Router's _business_values_from_message)
survive when the chatflow ``conversation`` scope does not persist them.

Merge rules (audit §6):

- per task: ``business_refs`` first; chatflow ``conversation`` scope wins on
  key collision.
- across tasks: historical / suspended tasks first (in repository order);
  the active task is merged last, so its keys win on collision.

The workflow service is consulted via ``get_session_state``. ``BizError``
indicates that the chatflow session is missing or the state repository is
not configured; in either case the aggregator falls back to ``business_refs``
without propagating the error.
"""

from collections.abc import Mapping
from typing import Any, Protocol

from app.core.errors import BizError
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository


class _ChatflowStateReader(Protocol):
    """Minimal contract over WorkflowService.get_session_state.

    Declared inline so this module does not import WorkflowService and avoids
    a cross-module circular dependency.
    """

    def get_session_state(self, chatflow_id: int, session_id: str) -> dict[str, Any]:
        ...


class RuntimeLabBusinessContextAggregator:
    """Aggregates "what the user has already provided" across a runtime-lab session."""

    def __init__(
        self,
        repository: RuntimeLabRepository,
        workflow_service: _ChatflowStateReader | None,
    ) -> None:
        self._repository = repository
        self._workflow_service = workflow_service

    def collect(self, session_id: int) -> dict[str, Any]:
        """Return merged business context. Active task wins on key collision."""
        active_id = self._active_task_id(session_id)
        merged: dict[str, Any] = {}
        active_ctx: dict[str, Any] | None = None
        for task in self._repository.list_tasks(session_id):
            ctx = self._task_conversation_variables(task)
            if int(task["id"]) == active_id:
                active_ctx = ctx
                continue
            merged.update(ctx)
        if active_ctx is not None:
            merged.update(active_ctx)
        return merged

    def _task_conversation_variables(self, task: Mapping[str, Any]) -> dict[str, Any]:
        business_refs = task.get("business_refs") or {}
        merged: dict[str, Any] = (
            dict(business_refs) if isinstance(business_refs, Mapping) else {}
        )
        chatflow_id = task.get("chatflow_id")
        chatflow_session_id = task.get("chatflow_session_id")
        if not chatflow_id or not chatflow_session_id or self._workflow_service is None:
            return merged
        try:
            state = self._workflow_service.get_session_state(
                int(chatflow_id), str(chatflow_session_id)
            )
        except BizError:
            return merged
        variables = state.get("variables") or {} if isinstance(state, Mapping) else {}
        conversation = (
            variables.get("conversation") if isinstance(variables, Mapping) else None
        )
        if isinstance(conversation, Mapping):
            merged.update(dict(conversation))
        return merged

    def _active_task_id(self, session_id: int) -> int:
        active = self._repository.get_active_task(session_id)
        return int(active["id"]) if active else 0
