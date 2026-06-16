import time
from typing import Any

from app.modules.customer_assistant.domain.models import AssistantTurnResult, TaskItem, TaskStatus, WorkerResult
from app.modules.runtime_lab.domain.sop_adapter import (
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionStatus,
    SopRuntimeAdapter,
)


class ChatflowSopWorker:
    def __init__(self, adapter: SopRuntimeAdapter) -> None:
        self._adapter = adapter

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        checkpoint = _checkpoint_from_dict(task.checkpoint)
        request = SopExecutionRequest(
            runtime_session_id=task.session_id,
            runtime_task_id=task.id,
            sop_id=task.worker_ref,
            message=message,
            checkpoint=checkpoint,
            collected=dict(checkpoint.collected if checkpoint else task.input_snapshot),
            business_refs=dict(task.input_snapshot),
            metadata={
                "channel": "customer-assistant",
                "source": "customer_assistant",
                "actor": "operator",
                "sop_key": task.worker_ref,
                "task_id": str(task.id or ""),
                "task_key": task.task_key,
                "session_id": str(task.session_id),
                "route_id": str(task.input_snapshot.get("route_id") or task.input_snapshot.get("routeId") or ""),
                "route_turn_id": str(task.input_snapshot.get("route_turn_id") or task.input_snapshot.get("routeTurnId") or ""),
                "intent_key": str(task.input_snapshot.get("intent_key") or task.input_snapshot.get("intentKey") or ""),
            },
        )
        result = self._adapter.continue_sop(request) if checkpoint else self._adapter.start_sop(request)
        status = _task_status(result.status)
        proposed_actions = _proposed_actions(task, result.to_dict()) if status == TaskStatus.COMPLETED else []
        chatflow_meta = _chatflow_meta(result.checkpoint.to_dict())
        evidence = {"sopId": task.worker_ref, "currentStep": result.current_step}
        if chatflow_meta:
            if chatflow_meta.get("runtimeVersion"):
                evidence["runtimeVersion"] = chatflow_meta.get("runtimeVersion")
            if chatflow_meta.get("runtimeRefs"):
                evidence["chatflowRuntimeRefs"] = dict(chatflow_meta["runtimeRefs"])
            if chatflow_meta.get("fallbackReason"):
                evidence["fallbackReason"] = chatflow_meta.get("fallbackReason")
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=status,
            operator_recommendation=_operator_recommendation(task, result.to_dict()),
            customer_reply_draft=result.reply or result.pending_prompt,
            missing_fields=[result.pending_prompt] if status == TaskStatus.WAITING and result.pending_prompt else [],
            evidence=evidence,
            proposed_actions=proposed_actions,
            checkpoint=result.checkpoint.to_dict(),
            events=_chatflow_worker_events(result.events),
            error=_chatflow_error(result.error),
        )


class StubQaWorker:
    def __init__(self, delay_seconds: float = 0.0) -> None:
        self._delay_seconds = delay_seconds

    def run(self, task: TaskItem, message: str) -> WorkerResult:
        if self._delay_seconds > 0:
            time.sleep(self._delay_seconds)
        answer = "经济舱通常可免费携带一件手提行李，托运行李额以客票规则和航司政策为准。"
        return WorkerResult(
            task_id=int(task.id or 0),
            worker_type=task.worker_type,
            status=TaskStatus.COMPLETED,
            operator_recommendation=f"已按规则回答行李问题：{message}",
            customer_reply_draft=answer,
            evidence={"source": "stub_qa", "topic": "baggage_allowance"},
            events=[{"type": "worker_result_received", "source": "stub_qa"}],
        )


class RecommendationAggregator:
    def aggregate(
        self,
        run_id: int,
        session_id: int,
        task_summaries: list[dict[str, Any]],
        worker_results: list[WorkerResult],
        proposed_actions: list[dict[str, Any]],
        events: list[dict[str, Any]],
    ) -> AssistantTurnResult:
        operator_lines = ["Operator recommendations:"]
        customer_lines: list[str] = []
        for result in worker_results:
            if result.operator_recommendation:
                operator_lines.append(f"- {result.operator_recommendation}")
            if result.customer_reply_draft:
                customer_lines.append(result.customer_reply_draft)
        if proposed_actions:
            operator_lines.append(f"- 待人工确认动作 {len(proposed_actions)} 个。")
        return AssistantTurnResult(
            run_id=run_id,
            session_id=session_id,
            reply_type="DRAFT",
            operator_recommendation="\n".join(operator_lines),
            customer_reply_draft="\n".join(customer_lines) or "暂无可发送给客户的草稿。",
            task_summaries=task_summaries,
            proposed_actions=proposed_actions,
            events=events,
        )


def _checkpoint_from_dict(data: dict[str, Any]) -> SopCheckpoint | None:
    if not data:
        return None
    return SopCheckpoint(
        sop_runtime_id=str(data.get("sopRuntimeId") or data.get("sop_runtime_id") or ""),
        current_node_id=str(data.get("currentNodeId") or data.get("current_node_id") or ""),
        current_step=str(data.get("currentStep") or data.get("current_step") or ""),
        pending_prompt=str(data.get("pendingPrompt") or data.get("pending_prompt") or ""),
        collected=dict(data.get("collected") or {}),
        scoped_variables=dict(data.get("scopedVariables") or data.get("scoped_variables") or {}),
        version=int(data.get("version") or 1),
    )


def _chatflow_meta(checkpoint: dict[str, Any]) -> dict[str, Any]:
    scoped_variables = checkpoint.get("scopedVariables") or checkpoint.get("scoped_variables") or {}
    if not isinstance(scoped_variables, dict):
        return {}
    meta = scoped_variables.get("__chatflow")
    return dict(meta) if isinstance(meta, dict) else {}


def _chatflow_error(error: dict[str, Any] | None) -> dict[str, Any] | None:
    if not error:
        return None
    normalized = dict(error)
    if normalized.get("code") == "CHATFLOW_V2_START_FAILED":
        normalized.setdefault("runtimeCode", normalized["code"])
        normalized["code"] = "CHATFLOW_START_FAILED"
    return normalized


def _chatflow_worker_events(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    live_events: list[dict[str, Any]] = []
    compatibility_events: list[dict[str, Any]] = []
    for event in events:
        projected = dict(event)
        source = str(projected.get("source") or "chatflow_sop")
        if source == "chatflow_runtime_v2":
            live_events.append(
                {
                    "type": str(projected.get("type") or "chatflow_runtime_event"),
                    "source": source,
                    "payload": _chatflow_live_event_payload(projected),
                }
            )
        compatibility_events.append(
            {
                "type": "worker_result_received",
                "source": "chatflow_sop",
                "payload": projected,
            }
        )
    return [*live_events, *compatibility_events]


def _chatflow_live_event_payload(event: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "type": str(event.get("type") or ""),
        "sourceKind": "chatflow",
        "eventMode": "live",
        "runtimeRunId": event.get("runtimeRunId"),
        "sourceEventId": event.get("sourceEventId"),
        "sourceSequence": event.get("sourceSequence"),
        "nodeKey": str(event.get("nodeKey") or ""),
        "callerContext": dict(event.get("callerContext") or {}),
    }
    if event.get("checkpointId") is not None:
        payload["checkpointId"] = event.get("checkpointId")
    return payload


def _task_status(status: SopExecutionStatus) -> TaskStatus:
    if status == SopExecutionStatus.COMPLETED:
        return TaskStatus.COMPLETED
    if status == SopExecutionStatus.FAILED:
        return TaskStatus.FAILED
    return TaskStatus.WAITING


def _operator_recommendation(task: TaskItem, result: dict[str, Any]) -> str:
    status = str(result.get("status") or "")
    step = str(result.get("currentStep") or "")
    return f"{task.task_key} worker {status} at {step}".strip()


def _proposed_actions(task: TaskItem, result: dict[str, Any]) -> list[dict[str, Any]]:
    if task.task_key != "refund_ticket":
        return []
    collected = dict(result.get("collected") or {})
    order_no = str(collected.get("order_no") or collected.get("orderNo") or "UNKNOWN")
    return [
        {
            "actionKey": f"{task.task_key}:submit_refund:{order_no}",
            "actionType": "submit_refund",
            "title": "提交退票申请",
            "payload": {"orderNo": order_no},
        }
    ]
