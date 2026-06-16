from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.modules.chat.domain.service import ChatService
from app.modules.chat.infra.repository import ChatRepository
from app.modules.chat.web.schemas import ChatMessageCreateRequest, ChatSessionCreateRequest
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.workflow.api.facade import WorkflowFacade
from app.modules.workflow.domain.engine import WorkflowExecutionEngine
from app.modules.workflow.infra.repository import WorkflowRepository


@dataclass(frozen=True)
class TargetExecutionResult:
    target_type: str
    target_id: int
    output: str
    target_run_id: int | None
    status: str
    debug_url: str
    evidence_summary: dict[str, Any]


class EvaluationTargetAdapter(Protocol):
    target_type: str

    def execute(self, target_id: int, content: str) -> TargetExecutionResult:
        ...


class EvaluationTargetAccessPolicy:
    required_permission = "evaluation:run"

    def __init__(self, request_context: RequestContext | None) -> None:
        self._request_context = request_context

    def ensure_can_run_target(self, target_type: str, target_id: int) -> None:
        if self._request_context is None or self._request_context.source == "local":
            return
        if self.required_permission in self._request_context.permissions:
            return
        raise BizError(
            ErrorCode.FORBIDDEN,
            f"Missing permission {self.required_permission} to run {target_type} target {target_id}",
        )


class EvaluationTargetRunner:
    def __init__(self, session: Session, request_context: RequestContext | None = None) -> None:
        self._policy = EvaluationTargetAccessPolicy(request_context)
        self._adapters: dict[str, EvaluationTargetAdapter] = {
            "AGENT": AgentTargetAdapter(session),
            "WORKFLOW": FlowTargetAdapter(session, "WORKFLOW"),
            "CHATFLOW": FlowTargetAdapter(session, "CHATFLOW"),
        }

    def execute(self, target_type: str, target_id: int, content: str) -> TargetExecutionResult:
        self._policy.ensure_can_run_target(target_type, target_id)
        adapter = self._adapters.get(target_type)
        if adapter is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Unsupported evaluation target type")
        return adapter.execute(target_id, content)


class AgentTargetAdapter:
    target_type = "AGENT"

    def __init__(self, session: Session) -> None:
        self._session = session

    def execute(self, target_id: int, content: str) -> TargetExecutionResult:
        chat_service = ChatService(
            ChatRepository(self._session),
            knowledge_facade=KnowledgeFacade(self._session),
            workflow_facade=WorkflowFacade(self._session),
            mcp_facade=McpFacade(self._session),
            model_facade=ProviderModelFacade(self._session),
        )
        chat_session = chat_service.create_session(ChatSessionCreateRequest(agentId=target_id))
        turn = chat_service.send_message(
            int(chat_session["id"]),
            ChatMessageCreateRequest(content=content, stream=False),
        )
        preview_run_id = int(chat_session["id"])
        debug_url = f"/agents/{target_id}/workbench?previewRunId={preview_run_id}&debug=1"
        return _target_result(
            target_type=self.target_type,
            target_id=target_id,
            output=str(turn["assistantMessage"]["content"]),
            target_run_id=preview_run_id,
            status="SUCCEEDED",
            debug_url=debug_url,
        )


class FlowTargetAdapter:
    def __init__(self, session: Session, flow_type: str) -> None:
        self.target_type = flow_type
        self._repository = WorkflowRepository(session)
        self._knowledge_facade = KnowledgeFacade(session)

    def execute(self, target_id: int, content: str) -> TargetExecutionResult:
        engine = WorkflowExecutionEngine(
            self._repository,
            knowledge_facade=self._knowledge_facade,
            flow_type=self.target_type,
        )
        result = engine.run(target_id, {"userMessage": content})
        run_id = int(result.run_id)
        debug_url = _flow_debug_url(self.target_type, target_id, run_id)
        return _target_result(
            target_type=self.target_type,
            target_id=target_id,
            output=_string_output(result.output),
            target_run_id=run_id,
            status=result.status,
            debug_url=debug_url,
        )


def _target_result(
    *,
    target_type: str,
    target_id: int,
    output: str,
    target_run_id: int | None,
    status: str,
    debug_url: str,
) -> TargetExecutionResult:
    evidence_summary = {
        "targetType": target_type,
        "targetId": target_id,
        "runId": target_run_id,
        "status": status,
        "debugUrl": debug_url,
    }
    return TargetExecutionResult(
        target_type=target_type,
        target_id=target_id,
        output=output,
        target_run_id=target_run_id,
        status=status,
        debug_url=debug_url,
        evidence_summary=evidence_summary,
    )


def _flow_debug_url(flow_type: str, target_id: int, run_id: int) -> str:
    prefix = "chatflows" if flow_type == "CHATFLOW" else "workflows"
    return f"/{prefix}/{target_id}/canvas?runId={run_id}&debug=1"


def _string_output(output: dict[str, Any]) -> str:
    if "answer" in output:
        return str(output["answer"])
    if "output" in output:
        return str(output["output"])
    if len(output) == 1:
        return str(next(iter(output.values())))
    return str(output)
