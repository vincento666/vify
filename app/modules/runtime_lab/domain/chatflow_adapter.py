import re
from collections.abc import Mapping
from typing import Any, cast

from app.core.errors import BizError
from app.modules.runtime_lab.domain.sop_adapter import (
    SopRuntimeAdapter,
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionResult,
    SopExecutionStatus,
)
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.web.schemas import WorkflowResumeRequest, WorkflowRunRequest


class ChatflowSopRuntimeAdapter:
    def __init__(
        self,
        workflow_service: WorkflowService,
        sop_chatflow_ids: dict[str, int],
        fallback_adapter: SopRuntimeAdapter | None = None,
    ) -> None:
        self._workflow_service = workflow_service
        self._sop_chatflow_ids = dict(sop_chatflow_ids)
        self._fallback_adapter = fallback_adapter

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        chatflow_id = self._chatflow_id(request.sop_id)
        if chatflow_id is None:
            if self._fallback_adapter is not None:
                return self._fallback_adapter.start_sop(request)
            return _failure(request, "SOP_CHATFLOW_NOT_BOUND", f"SOP is not bound to Chatflow: {request.sop_id}")
        try:
            run = self._workflow_service.execute(chatflow_id, WorkflowRunRequest(input=_runtime_input(request)))
        except BizError as exc:
            return _failure(request, "CHATFLOW_START_FAILED", str(exc))
        return self._result_from_run(request, chatflow_id, run)

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return self._resume_or_run(request, fallback_operation="continue")

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        if self._chatflow_id(request.sop_id) is None and self._fallback_adapter is not None:
            return self._fallback_adapter.suspend_sop(request)
        if request.checkpoint is not None:
            return request.checkpoint
        return _checkpoint(
            request,
            chatflow_id=self._chatflow_id(request.sop_id) or 0,
            run_id=0,
            event_id=None,
            checkpoint_id=None,
            session_id="",
            current_step="",
            pending_prompt="",
            collected=request.collected,
            resume_mode="missing",
        )

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return self._resume_or_run(request, fallback_operation="resume")

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        if self._chatflow_id(sop_id) is None and self._fallback_adapter is not None:
            return self._fallback_adapter.is_interruptible(sop_id, step_id)
        return bool(step_id) and step_id not in {"confirm", "confirm_1", "completed"}

    def _resume_or_run(self, request: SopExecutionRequest, *, fallback_operation: str) -> SopExecutionResult:
        chatflow_id = self._chatflow_id(request.sop_id)
        if chatflow_id is None:
            if self._fallback_adapter is not None:
                if fallback_operation == "continue":
                    return self._fallback_adapter.continue_sop(request)
                return self._fallback_adapter.resume_sop(request)
            return _failure(request, "SOP_CHATFLOW_NOT_BOUND", f"SOP is not bound to Chatflow: {request.sop_id}")
        if request.checkpoint is None:
            return _failure(request, "CHATFLOW_CHECKPOINT_REQUIRED", "Chatflow checkpoint is required")
        meta = _chatflow_meta(request.checkpoint)
        run_id = _int(meta.get("runId"))
        event_id = _optional_int(meta.get("eventId"))
        resume_mode = str(meta.get("resumeMode") or "event")
        try:
            if resume_mode == "event" and run_id > 0 and event_id is not None:
                run = self._workflow_service.resume_run(
                    chatflow_id,
                    run_id,
                    WorkflowResumeRequest(
                        eventId=event_id,
                        resumeData=_resume_data(request),
                        idempotencyKey=str(request.metadata.get("idempotencyKey") or "") or None,
                    ),
                )
            else:
                run = self._workflow_service.execute(
                    chatflow_id,
                    WorkflowRunRequest(input=_runtime_input(request, resume_node=request.checkpoint.current_node_id)),
                )
        except BizError as exc:
            return _failure(request, "CHATFLOW_RESUME_FAILED", str(exc))
        return self._result_from_run(request, chatflow_id, run)

    def _result_from_run(
        self,
        request: SopExecutionRequest,
        chatflow_id: int,
        run: Mapping[str, Any],
    ) -> SopExecutionResult:
        raw_status = str(run.get("status") or "")
        output = _as_mapping(run.get("output"))
        if raw_status == "SUCCEEDED":
            status = SopExecutionStatus.COMPLETED
            current_step = "completed"
            pending_prompt = ""
        elif raw_status == "INTERRUPTED":
            status = SopExecutionStatus.WAITING
            current_step = _pending_node(output, run)
            pending_prompt = _pending_prompt(output, current_step)
        else:
            return _failure(request, "CHATFLOW_RUN_FAILED", f"Chatflow run failed: {raw_status}")

        collected = _collected(request, output, self._session_variables(chatflow_id, run))
        event_checkpoint_id = _event_checkpoint_id(run)
        checkpoint = _checkpoint(
            request,
            chatflow_id=chatflow_id,
            run_id=_int(run.get("runId")),
            event_id=_event_id(run),
            checkpoint_id=event_checkpoint_id or _optional_int(run.get("checkpointId")),
            session_id=str(run.get("sessionId") or ""),
            current_step=current_step,
            pending_prompt=pending_prompt,
            collected=collected,
            resume_mode=_resume_mode(status, run),
        )
        return SopExecutionResult(
            status=status,
            current_step=current_step,
            reply=_reply(status, pending_prompt, output),
            pending_prompt=pending_prompt,
            checkpoint=checkpoint,
            collected=collected,
            business_refs=collected,
            events=[dict(event) for event in _as_list(run.get("events")) if isinstance(event, Mapping)],
            error=None,
        )

    def _chatflow_id(self, sop_id: str) -> int | None:
        return self._sop_chatflow_ids.get(sop_id)

    def _session_variables(self, chatflow_id: int, run: Mapping[str, Any]) -> Mapping[str, Any]:
        session_id = str(run.get("sessionId") or "")
        if not session_id:
            return {}
        try:
            state = self._workflow_service.get_session_state(chatflow_id, session_id)
        except BizError:
            return {}
        variables = state.get("variables") if isinstance(state, Mapping) else {}
        return variables if isinstance(variables, Mapping) else {}


def _runtime_input(request: SopExecutionRequest, resume_node: str | None = None) -> dict[str, Any]:
    conversation_id = str(
        request.metadata.get("conversationId")
        or request.metadata.get("conversation_id")
        or f"runtime-lab-{request.runtime_session_id}-{request.runtime_task_id or 'new'}-{request.sop_id}"
    )
    runtime_input: dict[str, Any] = {
        "sys.query": request.message,
        "sys.conversation_id": conversation_id,
        "sys.user_id": str(request.metadata.get("userId") or request.metadata.get("user_id") or ""),
        "sys.channel": str(request.metadata.get("channel") or "runtime-lab"),
    }
    if resume_node:
        resume: dict[str, Any] = {resume_node: _resume_data(request)}
        for collected_node_id in _collected_node_ids(request.checkpoint):
            if collected_node_id != resume_node and request.checkpoint is not None and request.checkpoint.collected:
                resume[collected_node_id] = {
                    "answer": request.message,
                    "collected": dict(request.checkpoint.collected),
                }
        runtime_input["resume"] = resume
    return runtime_input


def _resume_data(request: SopExecutionRequest) -> dict[str, Any]:
    data: dict[str, Any] = {"answer": request.message}
    if request.checkpoint is not None and request.checkpoint.collected:
        data["collected"] = dict(request.checkpoint.collected)
    return data


def _pending_node(output: Mapping[str, Any], run: Mapping[str, Any]) -> str:
    interrupt = _as_mapping(output.get("interrupt"))
    node_key = str(interrupt.get("nodeKey") or "")
    if node_key:
        return node_key
    events = _as_list(run.get("events"))
    for event in reversed(events):
        if isinstance(event, Mapping) and str(event.get("type") or "") == "interrupt":
            payload = _as_mapping(event.get("payload"))
            return str(payload.get("nodeKey") or "")
    return ""


def _pending_prompt(output: Mapping[str, Any], current_step: str) -> str:
    followup = str(output.get("followup") or "")
    missing = output.get("missing") if isinstance(output.get("missing"), list) else []
    if followup:
        return followup
    interrupt = _as_mapping(output.get("interrupt"))
    prompt = str(interrupt.get("question") or interrupt.get("prompt") or "")
    if prompt:
        return prompt
    if missing:
        return f"请补充 {', '.join(str(item) for item in missing)}"
    return current_step


def _collected(
    request: SopExecutionRequest,
    output: Mapping[str, Any],
    session_variables: Mapping[str, Any],
) -> dict[str, Any]:
    collected = dict(request.checkpoint.collected) if request.checkpoint is not None else dict(request.collected)
    collected.update(_business_values_from_message(request.message))
    conversation_variables = session_variables.get("conversation")
    if isinstance(conversation_variables, Mapping):
        collected.update(dict(conversation_variables))
    node_outputs = session_variables.get("node_outputs")
    if isinstance(node_outputs, Mapping):
        for node_output in node_outputs.values():
            if not isinstance(node_output, Mapping):
                continue
            node_collected = node_output.get("collected")
            if isinstance(node_collected, Mapping):
                collected.update(dict(node_collected))
    raw_collected = output.get("collected")
    if isinstance(raw_collected, Mapping):
        collected.update(dict(raw_collected))
    final = output.get("final")
    if isinstance(final, str):
        for part in final.replace("|", " ").split():
            if part.startswith("order=") and "order_no" not in collected:
                collected["order_no"] = part.split("=", 1)[1]
            if part.startswith("phone=") and "phone" not in collected:
                collected["phone"] = part.split("=", 1)[1]
    return collected


def _business_values_from_message(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    order_match = re.search(r"(?:订单号|order_no|order)\s*[:：]?\s*([A-Za-z]{1,4}[-_]?\d{3,12})", text, re.IGNORECASE)
    if order_match:
        values["order_no"] = order_match.group(1)
    phone_match = re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
    if phone_match:
        values["phone"] = phone_match.group(1)
    passenger_match = re.search(r"乘机人\s*[:：]?\s*([A-Za-z\u4e00-\u9fff][A-Za-z0-9_\-\u4e00-\u9fff]{0,20})", text)
    if passenger_match:
        values["passenger_name"] = passenger_match.group(1)
    return values


def _checkpoint(
    request: SopExecutionRequest,
    *,
    chatflow_id: int,
    run_id: int,
    event_id: int | None,
    checkpoint_id: int | None,
    session_id: str,
    current_step: str,
    pending_prompt: str,
    collected: dict[str, Any],
    resume_mode: str,
) -> SopCheckpoint:
    scoped_variables: dict[str, Any] = {f"conversation.{key}": value for key, value in collected.items()}
    scoped_variables["__chatflow"] = {
        "chatflowId": chatflow_id,
        "runId": run_id,
        "eventId": event_id,
        "checkpointId": checkpoint_id,
        "sessionId": session_id,
        "resumeMode": resume_mode,
        "collectedNodeIds": _next_collected_node_ids(request, current_step, collected),
    }
    return SopCheckpoint(
        sop_runtime_id=f"chatflow:{chatflow_id}:{run_id}:{checkpoint_id or event_id or 0}",
        current_node_id=current_step,
        current_step=current_step,
        pending_prompt=pending_prompt,
        collected=dict(collected),
        scoped_variables=scoped_variables,
        version=1,
    )


def _resume_mode(status: SopExecutionStatus, run: Mapping[str, Any]) -> str:
    if status != SopExecutionStatus.WAITING:
        return "complete"
    checkpoint_id = _event_checkpoint_id(run)
    return "event" if checkpoint_id and checkpoint_id > 0 else "direct"


def _event_id(run: Mapping[str, Any]) -> int | None:
    events = _as_list(run.get("events"))
    for event in reversed(events):
        if isinstance(event, Mapping) and str(event.get("type") or "") == "interrupt":
            return _optional_int(event.get("id"))
    return None


def _event_checkpoint_id(run: Mapping[str, Any]) -> int | None:
    events = _as_list(run.get("events"))
    for event in reversed(events):
        if isinstance(event, Mapping) and str(event.get("type") or "") == "interrupt":
            return _optional_int(event.get("checkpointId"))
    return None


def _chatflow_meta(checkpoint: SopCheckpoint) -> Mapping[str, Any]:
    meta = checkpoint.scoped_variables.get("__chatflow")
    return meta if isinstance(meta, Mapping) else {}


def _collected_node_ids(checkpoint: SopCheckpoint | None) -> list[str]:
    if checkpoint is None:
        return []
    raw_node_ids = _chatflow_meta(checkpoint).get("collectedNodeIds")
    if not isinstance(raw_node_ids, list):
        return []
    return [str(node_id) for node_id in raw_node_ids if str(node_id)]


def _next_collected_node_ids(
    request: SopExecutionRequest,
    current_step: str,
    collected: Mapping[str, Any],
) -> list[str]:
    node_ids = _collected_node_ids(request.checkpoint)
    if request.checkpoint is None or not collected:
        return node_ids
    previous_node_id = request.checkpoint.current_node_id
    if previous_node_id and previous_node_id != current_step and previous_node_id not in node_ids:
        node_ids.append(previous_node_id)
    return node_ids


def _reply(status: SopExecutionStatus, pending_prompt: str, output: Mapping[str, Any]) -> str:
    if status == SopExecutionStatus.WAITING:
        return pending_prompt
    final = output.get("final")
    return str(final or "Chatflow SOP 已完成。")


def _failure(request: SopExecutionRequest, code: str, message: str) -> SopExecutionResult:
    checkpoint = _checkpoint(
        request,
        chatflow_id=0,
        run_id=0,
        event_id=None,
        checkpoint_id=None,
        session_id="",
        current_step="",
        pending_prompt="",
        collected={},
        resume_mode="failure",
    )
    return SopExecutionResult(
        status=SopExecutionStatus.FAILED,
        current_step="",
        reply="",
        pending_prompt="",
        checkpoint=checkpoint,
        collected={},
        business_refs={},
        events=[],
        error={"code": code, "message": message},
    )


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    parsed = _int(value)
    return parsed if parsed > 0 else None


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
