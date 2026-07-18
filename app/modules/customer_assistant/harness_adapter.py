from __future__ import annotations

from dataclasses import replace
from datetime import datetime
from typing import Any, Mapping

from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.modules.agent_execution import (
    AgentExecutionCapabilities,
    AgentExecutionCapabilityError,
    AgentExecutionStatus,
    SubagentExecutionRef,
)
from app.modules.customer_assistant.domain.access import ensure_customer_assistant_session_owner
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository


class CustomerAssistantExecutionAdapter:
    def __init__(
        self,
        repository: CustomerAssistantRepository,
        request_context: RequestContext | None = None,
    ) -> None:
        self._repository = repository
        self._request_context = request_context

    @property
    def provider(self) -> str:
        return "customer_assistant"

    @property
    def display_name(self) -> str:
        return "客服助手"

    @property
    def capabilities(self) -> AgentExecutionCapabilities:
        return AgentExecutionCapabilities(
            spawn=False,
            attach=True,
            observe=True,
            cancel=False,
        )

    def spawn(
        self,
        *,
        parent_execution_id: str,
        input_payload: dict[str, Any],
    ) -> SubagentExecutionRef:
        raise AgentExecutionCapabilityError("spawn")

    def attach(
        self,
        *,
        parent_execution_id: str,
        session_id: int,
        run_id: int,
    ) -> SubagentExecutionRef:
        return replace(
            self._resolve(session_id=session_id, run_id=run_id),
            parent_execution_id=parent_execution_id,
        )

    def observe(self, *, execution_id: str) -> SubagentExecutionRef:
        run_id = _run_id_from_execution_id(execution_id)
        run = self._repository.get_run(run_id)
        if run is None:
            raise BizError(ErrorCode.NOT_FOUND, "Customer assistant sub-agent run not found")
        return self._resolve(session_id=int(run["session_id"]), run_id=run_id)

    def cancel(self, *, execution_id: str, actor_id: str) -> SubagentExecutionRef:
        raise AgentExecutionCapabilityError("cancel")

    def _resolve(self, *, session_id: int, run_id: int) -> SubagentExecutionRef:
        session = self._repository.get_session(session_id)
        run = self._repository.get_run(run_id)
        if session is None or run is None or int(run["session_id"]) != session_id:
            raise BizError(ErrorCode.NOT_FOUND, "Customer assistant sub-agent run not found")
        ensure_customer_assistant_session_owner(session, self._request_context)
        status = AgentExecutionStatus.from_value(run.get("status"))
        return SubagentExecutionRef(
            execution_id=sub_agent_run_public_id(run_id),
            provider=self.provider,
            child_run_id=str(run_id),
            parent_execution_id=None,
            agent_type="customer_assistant",
            display_name=self.display_name,
            status=status,
            current_summary=_current_summary(self._repository, session_id=session_id, run_id=run_id),
            started_at=_iso(run.get("started_at")),
            completed_at=_iso(run.get("completed_at")),
            status_ref=result_ref(run_id),
            event_stream_ref=event_stream_ref(session_id),
            result_ref=result_ref(run_id),
            capabilities=self.capabilities,
            scope=_scope(session),
            audit={
                "source": "customer_assistant_run",
                "runId": run_id,
                "sessionId": session_id,
                **(self._request_context.audit_metadata() if self._request_context is not None else {}),
            },
            runtime_refs=reserved_worker_async_refs(run_id=run_id, session_id=session_id),
            cancellation=unsupported_cancellation(),
        )


def create_customer_assistant_execution_adapter(
    session: Session,
    request_context: RequestContext | Mapping[str, Any] | None,
) -> CustomerAssistantExecutionAdapter:
    return CustomerAssistantExecutionAdapter(
        CustomerAssistantRepository(session),
        _request_context(request_context),
    )


def sub_agent_run_public_id(run_id: int) -> str:
    return f"customer-assistant-run-{run_id}"


def event_stream_ref(session_id: int, after_sequence: int = 0) -> str:
    return f"/api/v1/customer-assistant/sessions/{session_id}/events/stream?afterSequence={after_sequence}"


def result_ref(run_id: int) -> str:
    return f"/api/v1/customer-assistant/runs/{run_id}"


def unsupported_cancellation() -> dict[str, Any]:
    return {
        "supported": False,
        "reason": "Customer-assistant sub-agent cancellation is not implemented.",
    }


def reserved_worker_async_refs(run_id: int | None = None, session_id: int | None = None) -> dict[str, Any]:
    return {
        "supported": False,
        "workerRunId": None,
        "workerStatusRef": None,
        "workerEventsRef": None,
        "workerEventStreamRef": None,
        "workerResultRef": None,
        "reason": "No durable async worker run exists for this sub-agent execution.",
    }


def summarize_sub_agent_result(run_snapshot: dict[str, Any]) -> str:
    result = run_snapshot.get("result") or {}
    if not isinstance(result, dict):
        return "status=unknown"
    parts = [
        f"status={run_snapshot.get('status')}",
        f"runId={result.get('runId')}",
    ]
    if result.get("operatorRecommendation"):
        parts.append(f"operatorRecommendation={result['operatorRecommendation']}")
    if result.get("customerReplyDraft"):
        parts.append(f"customerReplyDraft={result['customerReplyDraft']}")
    return "; ".join(parts)


def _current_summary(
    repository: CustomerAssistantRepository,
    *,
    session_id: int,
    run_id: int,
) -> str:
    events = [
        event
        for event in repository.list_events(session_id)
        if int(event.get("run_id") or 0) == run_id
    ]
    if not events:
        return ""
    latest = events[-1]
    payload = dict(latest.get("payload") or {})
    for key in ("summary", "customerReplyDraft", "operatorRecommendation", "stage", "status"):
        value = str(payload.get(key) or "").strip()
        if value:
            return value
    return str(latest.get("type") or "").strip()


def _scope(session: dict[str, Any]) -> dict[str, Any]:
    context = dict(session.get("context_json") or {})
    host_context = context.get("hostContext")
    if not isinstance(host_context, dict):
        return {"tenantId": "local", "orgId": "local"}
    return {
        "tenantId": str(host_context.get("tenantId") or ""),
        "orgId": str(host_context.get("orgId") or ""),
    }


def _iso(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _run_id_from_execution_id(execution_id: str) -> int:
    prefix = "customer-assistant-run-"
    if not execution_id.startswith(prefix):
        raise BizError(ErrorCode.BAD_REQUEST, "Invalid customer assistant execution id")
    try:
        return int(execution_id.removeprefix(prefix))
    except ValueError as exc:
        raise BizError(ErrorCode.BAD_REQUEST, "Invalid customer assistant execution id") from exc


def _request_context(
    value: RequestContext | Mapping[str, Any] | None,
) -> RequestContext | None:
    if value is None or isinstance(value, RequestContext):
        return value
    tenant_id = str(value.get("tenantId") or "local")
    actor_id = str(value.get("actorId") or value.get("userId") or "local-user")
    return RequestContext(
        actor_id=actor_id,
        actor_name=str(value.get("actorName") or actor_id),
        tenant_id=tenant_id,
        org_id=str(value.get("orgId") or tenant_id),
        roles=tuple(str(item) for item in value.get("roles") or ()),
        permissions=tuple(str(item) for item in value.get("permissions") or ()),
        request_id=str(value.get("requestId") or ""),
        source=str(value.get("source") or "durable-scope"),
        locale=str(value.get("locale") or "zh-CN"),
    )


__all__ = [
    "CustomerAssistantExecutionAdapter",
    "create_customer_assistant_execution_adapter",
    "event_stream_ref",
    "reserved_worker_async_refs",
    "result_ref",
    "sub_agent_run_public_id",
    "summarize_sub_agent_result",
    "unsupported_cancellation",
]
