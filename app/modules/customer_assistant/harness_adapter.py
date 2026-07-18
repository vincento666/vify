from __future__ import annotations

from typing import Any

from app.modules.agent_execution import ChildExecutionReference


class CustomerAssistantExecutionAdapter:
    @property
    def tool_name(self) -> str:
        return "customer_assistant_subagent_bridge"

    @property
    def description(self) -> str:
        return "读取客服助手子任务引用，供上层助手检查任务状态。"

    @property
    def read_resources(self) -> list[str]:
        return ["customer_assistant:session:{sessionId}", "customer_assistant:run:{runId}"]

    def resolve(self, *, session_id: int, run_id: int) -> ChildExecutionReference:
        return ChildExecutionReference(
            agent_type="customer_assistant",
            child_run_id=sub_agent_run_public_id(run_id),
            event_stream_ref=event_stream_ref(session_id),
            result_ref=result_ref(run_id),
            worker_async_refs=reserved_worker_async_refs(run_id=run_id, session_id=session_id),
            cancellation=unsupported_cancellation(),
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
        "reason": "Customer-assistant sub-agent cancellation is not implemented in 052.",
    }


def reserved_worker_async_refs(run_id: int | None = None, session_id: int | None = None) -> dict[str, Any]:
    return {
        "supported": False,
        "workerRunId": None,
        "workerStatusRef": None,
        "workerEventsRef": None,
        "workerEventStreamRef": None,
        "workerResultRef": None,
        "reason": "No durable async worker run exists for this sub-agent payload yet.",
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
