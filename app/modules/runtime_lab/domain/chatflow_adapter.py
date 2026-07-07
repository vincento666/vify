import re
import time
from collections.abc import Mapping
from typing import Any, cast

from app.core.errors import BizError
from app.modules.workflow.domain.runtime_invocation_gateway import RuntimeInvocationGateway
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.runtime_lab.domain.sop import missing_chatflow_binding_error
from app.modules.runtime_lab.domain.sop_adapter import (
    SopRuntimeAdapter,
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionResult,
    SopExecutionStatus,
)
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.web.schemas import WorkflowResumeRequest, WorkflowRunRequest


CHATFLOW_SOP_V2_BRIDGE_WAIT_SECONDS = 3.0
CHATFLOW_SOP_V2_BRIDGE_POLL_SECONDS = 0.05


class ChatflowSopRuntimeAdapter:
    def __init__(
        self,
        workflow_service: WorkflowService,
        sop_chatflow_ids: dict[str, int],
        fallback_adapter: SopRuntimeAdapter | None = None,
        runtime_v2_service: ChatflowRuntimeV2Service | None = None,
        runtime_invocation_gateway: RuntimeInvocationGateway | None = None,
        runtime_invocation_mode: str = "sync",
        fallback_on_missing_chatflow: bool = False,
    ) -> None:
        self._workflow_service = workflow_service
        self._sop_chatflow_ids = dict(sop_chatflow_ids)
        self._fallback_adapter = fallback_adapter
        self._runtime_v2_service = runtime_v2_service
        self._runtime_invocation_gateway = runtime_invocation_gateway
        if self._runtime_invocation_gateway is None and runtime_v2_service is not None:
            self._runtime_invocation_gateway = RuntimeInvocationGateway(runtime_v2_service)
        self._runtime_invocation_mode = _runtime_invocation_mode(runtime_invocation_mode)
        self._fallback_on_missing_chatflow = fallback_on_missing_chatflow

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        chatflow_id = self._chatflow_id(request.sop_id)
        if chatflow_id is None:
            return _missing_chatflow_binding_failure(request)
        if self._runtime_invocation_gateway is not None:
            v2_result = self._start_sop_v2(request, chatflow_id)
            if v2_result is not None:
                return v2_result
        return self._start_sop_v1(request, chatflow_id, fallback_events=[])

    def _start_sop_v1(
        self,
        request: SopExecutionRequest,
        chatflow_id: int,
        *,
        fallback_events: list[dict[str, Any]],
        fallback_reason: str = "",
    ) -> SopExecutionResult:
        try:
            run = self._workflow_service.execute(chatflow_id, WorkflowRunRequest(input=_runtime_input(request)))
        except BizError as exc:
            if self._can_fallback_missing_chatflow(exc):
                return self._start_configured_fallback(
                    request,
                    chatflow_id=chatflow_id,
                    reason=str(exc),
                    fallback_events=fallback_events,
                    source="chatflow_legacy_fallback",
                )
            return _failure(request, "CHATFLOW_START_FAILED", str(exc))
        except Exception as exc:
            return _failure(request, "CHATFLOW_START_FAILED", str(exc))
        result = self._result_from_run(request, chatflow_id, run, fallback_reason=fallback_reason)
        if fallback_events:
            return _with_prefixed_events(result, fallback_events)
        return result

    def _start_sop_v2(self, request: SopExecutionRequest, chatflow_id: int) -> SopExecutionResult | None:
        assert self._runtime_invocation_gateway is not None
        try:
            if self._runtime_invocation_mode == "async":
                invocation = self._runtime_invocation_gateway.start_and_stream_ref(
                    owner_id=chatflow_id,
                    input_data=_runtime_input(request),
                    idempotency_key=_v2_idempotency_key(request),
                )
                result = _async_pending_result(request, chatflow_id, invocation)
                return _with_prefixed_events(result, [{"type": "chatflow_v2_selected", "chatflowId": chatflow_id}])
            invocation = self._runtime_invocation_gateway.start_and_wait(
                owner_id=chatflow_id,
                input_data=_runtime_input(request),
                idempotency_key=_v2_idempotency_key(request),
            )
            run = _run_from_v2_invocation(invocation)
            result = self._result_from_run(request, chatflow_id, run, runtime_version=2)
            return _with_prefixed_events(result, [{"type": "chatflow_v2_selected", "chatflowId": chatflow_id}])
        except BizError as exc:
            message = str(exc)
            if _is_runtime_v2_compatibility_error(message):
                fallback = {"type": "chatflow_v2_fallback", "chatflowId": chatflow_id, "reason": message}
                return self._start_sop_v1(
                    request,
                    chatflow_id,
                    fallback_events=[fallback],
                    fallback_reason=message,
                )
            if self._can_fallback_missing_chatflow(exc):
                return self._start_configured_fallback(
                    request,
                    chatflow_id=chatflow_id,
                    reason=message,
                    source="chatflow_v2_fallback",
                )
            return _failure(request, "CHATFLOW_START_FAILED", message, runtime_code="CHATFLOW_V2_START_FAILED")
        except Exception as exc:
            return _failure(request, "CHATFLOW_START_FAILED", str(exc), runtime_code="CHATFLOW_V2_START_FAILED")

    def _start_configured_fallback(
        self,
        request: SopExecutionRequest,
        *,
        chatflow_id: int,
        reason: str,
        source: str,
        fallback_events: list[dict[str, Any]] | None = None,
    ) -> SopExecutionResult:
        assert self._fallback_adapter is not None
        events = [
            *(fallback_events or []),
            {"type": source, "chatflowId": chatflow_id, "reason": reason},
        ]
        result = self._fallback_adapter.start_sop(request)
        return _with_prefixed_events(result, events)

    def _can_fallback_missing_chatflow(self, exc: BizError) -> bool:
        return (
            self._fallback_on_missing_chatflow
            and self._fallback_adapter is not None
            and _is_missing_chatflow_error(exc)
        )

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return self._resume_or_run(request, fallback_operation="continue")

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        if self._chatflow_id(request.sop_id) is None:
            if request.checkpoint is not None:
                return request.checkpoint
            return _checkpoint(
                request,
                chatflow_id=0,
                run_id=0,
                event_id=None,
                checkpoint_id=None,
                session_id="",
                current_step="",
                pending_prompt="",
                collected=request.collected,
                resume_mode="missing_binding",
            )
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
        if self._chatflow_id(sop_id) is None:
            return False
        return bool(step_id) and step_id not in {"confirm", "confirm_1", "completed"}

    def _resume_or_run(self, request: SopExecutionRequest, *, fallback_operation: str) -> SopExecutionResult:
        chatflow_id = self._chatflow_id(request.sop_id)
        if chatflow_id is None:
            return _missing_chatflow_binding_failure(request)
        if request.checkpoint is None:
            return _failure(request, "CHATFLOW_CHECKPOINT_REQUIRED", "Chatflow checkpoint is required")
        meta = _chatflow_meta(request.checkpoint)
        run_id = _int(meta.get("runId"))
        event_id = _optional_int(meta.get("eventId"))
        resume_mode = str(meta.get("resumeMode") or "event")
        try:
            if _runtime_version_is_v2(meta.get("runtimeVersion")) and self._runtime_invocation_gateway is not None and run_id > 0:
                latest: Mapping[str, Any] = {}
                if self._runtime_v2_service is not None:
                    latest = self._runtime_v2_result(run_id)
                    if _v2_runtime_still_starting(latest):
                        latest = self._complete_starting_runtime_v2(run_id, latest)
                    if _v2_runtime_still_starting(latest):
                        return _async_pending_result_from_checkpoint(request, chatflow_id, meta, latest)
                    if _v2_runtime_terminal(latest):
                        if _v2_runtime_failed(latest):
                            return _v2_retryable_result_from_checkpoint(
                                request,
                                chatflow_id,
                                meta,
                                latest,
                                reason=_v2_failure_reason(latest),
                            )
                        return self._result_from_run(request, chatflow_id, latest, runtime_version=2)
                try:
                    invocation = self._runtime_invocation_gateway.resume_and_wait(
                        run_id=run_id,
                        resume_data=_resume_data(request),
                        idempotency_key=str(request.metadata.get("idempotencyKey") or _v2_idempotency_key(request)),
                    )
                except BizError as exc:
                    return _v2_retryable_result_from_checkpoint(request, chatflow_id, meta, latest, reason=str(exc))
                except Exception as exc:
                    return _v2_retryable_result_from_checkpoint(request, chatflow_id, meta, latest, reason=str(exc))
                run = _run_from_v2_invocation(
                    invocation,
                    session_id=str(meta.get("sessionId") or ""),
                    runtime_refs=dict(meta.get("runtimeRefs") or {}),
                )
                run = self._wait_for_v2_bridge_settled(run_id, run, previous_checkpoint=request.checkpoint)
                if _v2_runtime_failed(run):
                    return _v2_retryable_result_from_checkpoint(
                        request,
                        chatflow_id,
                        meta,
                        run,
                        reason=_v2_failure_reason(run),
                    )
                return self._result_from_run(request, chatflow_id, run, runtime_version=2)
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
        except Exception as exc:
            return _failure(request, "CHATFLOW_RESUME_FAILED", str(exc))
        return self._result_from_run(request, chatflow_id, run)

    def _runtime_v2_result(self, run_id: int) -> dict[str, Any]:
        if self._runtime_v2_service is None:
            return {}
        try:
            return self._runtime_v2_service.get_result(run_id)
        except Exception:
            return {}

    def _complete_starting_runtime_v2(self, run_id: int, fallback: Mapping[str, Any]) -> dict[str, Any]:
        if self._runtime_v2_service is None:
            return dict(fallback)
        try:
            self._runtime_v2_service.complete_run(run_id)
            return self._runtime_v2_service.get_result(run_id)
        except Exception:
            return dict(fallback)

    def _wait_for_v2_bridge_settled(
        self,
        run_id: int,
        run: Mapping[str, Any],
        *,
        previous_checkpoint: SopCheckpoint,
    ) -> dict[str, Any]:
        current = dict(run)
        if self._runtime_v2_service is None or _v2_bridge_settled(current, previous_checkpoint):
            return current
        deadline = time.monotonic() + CHATFLOW_SOP_V2_BRIDGE_WAIT_SECONDS
        while time.monotonic() < deadline:
            latest = self._runtime_v2_result(run_id)
            if latest:
                current = _v2_runtime_result_run(latest, fallback=current)
            if _v2_bridge_settled(current, previous_checkpoint):
                return current
            time.sleep(CHATFLOW_SOP_V2_BRIDGE_POLL_SECONDS)
        return current

    def _result_from_run(
        self,
        request: SopExecutionRequest,
        chatflow_id: int,
        run: Mapping[str, Any],
        runtime_version: int = 1,
        fallback_reason: str = "",
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

        collected = _sanitize_collected(request.sop_id, _collected(request, output, self._session_variables(chatflow_id, run)))
        missing_required = _missing_required_fields(request.sop_id, collected)
        if missing_required and current_step in {"confirm", "confirm_1", "completed"}:
            status = SopExecutionStatus.WAITING
            current_step = "collect"
            pending_prompt = _missing_required_prompt(missing_required)
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
            runtime_version=runtime_version,
            runtime_refs=dict(run.get("runtimeRefs") or {}),
            fallback_reason=fallback_reason,
        )
        return SopExecutionResult(
            status=status,
            current_step=current_step,
            reply=_reply(status, pending_prompt, output),
            pending_prompt=pending_prompt,
            checkpoint=checkpoint,
            collected=collected,
            business_refs=collected,
            events=(
                _project_events(run)
                if runtime_version == 2
                else [dict(event) for event in _as_list(run.get("events")) if isinstance(event, Mapping)]
            ),
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
    session_id = str(
        request.metadata.get("chatflowSessionId")
        or request.metadata.get("chatflow_session_id")
        or f"runtime-lab-{request.runtime_session_id}-{request.runtime_task_id or 'new'}-{request.sop_id}"
    )
    conversation_id = str(
        request.metadata.get("conversationId")
        or request.metadata.get("conversation_id")
        or session_id
    )
    runtime_input: dict[str, Any] = {
        "sys.query": request.message,
        "sys.session_id": session_id,
        "sys.conversation_id": conversation_id,
        "sys.user_id": str(request.metadata.get("userId") or request.metadata.get("user_id") or ""),
        "sys.channel": str(request.metadata.get("channel") or "runtime-lab"),
        "callerContext": _caller_context(request),
    }
    history = request.metadata.get("history") or request.metadata.get("conversationHistory")
    if isinstance(history, list):
        runtime_input["history"] = history
    inherited_context = request.metadata.get("inheritedContext") or request.metadata.get("inherited_context")
    if isinstance(inherited_context, Mapping):
        runtime_input["inherited_context"] = dict(inherited_context)
        for key, value in inherited_context.items():
            runtime_input[f"inherited_context.{key}"] = value
    inherited = dict(request.collected)
    inherited.update(_business_values_from_message(request.message))
    if inherited:
        runtime_input["collected"] = inherited
        runtime_input["conversation"] = inherited
        for key, value in inherited.items():
            runtime_input[f"conversation.{key}"] = value
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


def _caller_context(request: SopExecutionRequest) -> dict[str, str]:
    keys = ("sop_key", "route_id", "route_turn_id", "intent_key", "task_id", "session_id", "actor", "source")
    context = {key: str(request.metadata.get(key) or "") for key in keys}
    context["sop_key"] = context["sop_key"] or request.sop_id
    context["task_id"] = context["task_id"] or str(request.runtime_task_id or "")
    context["session_id"] = context["session_id"] or str(request.runtime_session_id)
    context["actor"] = context["actor"] or "operator"
    context["source"] = context["source"] or str(request.metadata.get("channel") or "runtime-lab")
    return context


def _resume_data(request: SopExecutionRequest) -> dict[str, Any]:
    data: dict[str, Any] = {"answer": request.message}
    collected = _business_values_from_message(request.message)
    if request.checkpoint is not None and request.checkpoint.collected:
        collected = {**request.checkpoint.collected, **collected}
    if collected:
        data["collected"] = collected
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
    current_turn_values = _business_values_from_message(request.message)
    collected.update(current_turn_values)
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
        for key, value in _business_values_from_text(final).items():
            if key not in collected:
                collected[key] = value
        for part in final.replace("|", " ").split():
            if part.startswith("order=") and "order_no" not in collected:
                collected["order_no"] = part.split("=", 1)[1]
            if part.startswith("phone=") and "phone" not in collected:
                collected["phone"] = part.split("=", 1)[1]
    collected.update(current_turn_values)
    return collected


def _business_values_from_message(text: str) -> dict[str, str]:
    return _business_values_from_text(text)


def _business_values_from_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    order_match = re.search(
        r"(?:订单编号|订单号|预订编号|order_no|order)\s*[:：]?\s*"
        r"([A-Za-z]{1,4}\d{2,8}(?:[-_]\d{3,12}){0,3}|[A-Za-z]{1,4}[-_]?\d{3,20})",
        text,
        re.IGNORECASE,
    )
    if order_match:
        values["order_no"] = order_match.group(1)
    phone_match = re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
    if phone_match:
        values["phone"] = phone_match.group(1)
    passenger_count_match = re.search(r"(\d+|[一二三四五六七八九十两]{1,3}|十几|二十几|三十几)个?人", text)
    if passenger_count_match and _looks_like_group_passenger_count_context(text):
        values["passenger_count"] = passenger_count_match.group(1)
    passenger_match = re.search(
        r"乘机人\s*[:：]?\s*"
        r"(?!和|及|与|、|还有|手机号|电话|信息|姓名|等下|稍后|后面|再给)"
        r"([A-Za-z\u4e00-\u9fff][A-Za-z0-9_\-\u4e00-\u9fff]{0,20})",
        text,
    )
    if passenger_match:
        passenger_name = _clean_passenger_name(passenger_match.group(1))
        if passenger_name:
            values["passenger_name"] = passenger_name
    values.update(_route_values_from_text(text))
    travel_time = _travel_time_from_text(text)
    if travel_time:
        values["travel_time"] = travel_time
    target_time_match = re.search(
        r"(?:改签|改到|改成|调整到|换到)[^，。,.]{0,20}?"
        r"((?:今天|明天|后天|大后天|周[一二三四五六日天]|星期[一二三四五六日天])"
        r"(?:上午|下午|晚上|中午|早上|晚间)?(?:\d{1,2}点(?:半)?(?:左右)?)?)",
        text,
    )
    if target_time_match:
        values["target_time"] = target_time_match.group(1)
    return values


AIRLINE_CITY_NAMES = (
    "北京",
    "上海",
    "广州",
    "深圳",
    "成都",
    "重庆",
    "杭州",
    "南京",
    "昆明",
    "武汉",
    "西安",
    "厦门",
    "青岛",
    "长沙",
    "郑州",
    "天津",
    "三亚",
    "海口",
    "大连",
    "沈阳",
    "哈尔滨",
    "乌鲁木齐",
    "贵阳",
    "南宁",
    "福州",
    "合肥",
    "济南",
    "宁波",
    "温州",
    "太原",
    "兰州",
    "银川",
    "呼和浩特",
    "拉萨",
    "西宁",
)


def _route_values_from_text(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    from_route = re.search(
        r"从([\u4e00-\u9fffA-Za-z]{2,16})(?:出发)?(?:到|去|飞)([\u4e00-\u9fffA-Za-z]{2,16}?)"
        r"(?:的?机票|的?航班|航班|，|,|。|$)",
        text,
    )
    if from_route is not None:
        origin = _clean_city(from_route.group(1))
        destination = _clean_city(from_route.group(2))
        if origin and not destination:
            destination = _contextual_destination_city(text, origin)
        if origin and destination:
            values["origin"] = origin
            values["destination"] = destination
            values["route"] = f"{origin}到{destination}"
            return values
    for origin in AIRLINE_CITY_NAMES:
        for destination in AIRLINE_CITY_NAMES:
            if origin == destination:
                continue
            if re.search(f"{re.escape(origin)}(?:到|去|飞){re.escape(destination)}", text):
                values["origin"] = origin
                values["destination"] = destination
                values["route"] = f"{origin}到{destination}"
                return values
    return values


def _contextual_destination_city(text: str, origin: str) -> str:
    for destination in AIRLINE_CITY_NAMES:
        if destination == origin:
            continue
        if re.search(f"(?:去|到|飞往|飞去){re.escape(destination)}", text):
            return destination
    return ""


def _travel_time_from_text(text: str) -> str:
    time_match = re.search(
        r"((?:今天|明天|后天|大后天|下?周[一二三四五六日天]|下?星期[一二三四五六日天])?"
        r"(?:早上|上午|中午|下午|晚上|夜里)?\s*\d{1,2}点(?:\d{1,2}分|半)?(?:左右)?)",
        text,
    )
    if time_match is not None:
        return time_match.group(1).replace(" ", "")
    date_period_match = re.search(
        r"((?:今天|明天|后天|大后天|下?周[一二三四五六日天]|下?星期[一二三四五六日天])"
        r"(?:早上|上午|中午|下午|晚上|夜里|晚间))",
        text,
    )
    if date_period_match is not None:
        return date_period_match.group(1)
    date_match = re.search(r"(今天|明天|后天|大后天|下?周[一二三四五六日天]|下?星期[一二三四五六日天])", text)
    return date_match.group(1) if date_match is not None else ""


def _clean_city(value: str) -> str:
    cleaned = value.strip()
    prefixes = ("我要订", "我要定", "我想订", "我想定", "帮我订", "帮我定", "订", "定", "买")
    for prefix in prefixes:
        if cleaned.startswith(prefix):
            cleaned = cleaned.removeprefix(prefix)
    cleaned = cleaned.strip()
    if cleaned in {"过去", "那边", "那里", "这边", "这里", "目的地"}:
        return ""
    return cleaned


def _clean_passenger_name(value: str) -> str:
    cleaned = value.strip()
    for prefix in ("是", "叫", "为"):
        if cleaned.startswith(prefix) and len(cleaned) > len(prefix):
            cleaned = cleaned.removeprefix(prefix).strip()
    if any(term in cleaned for term in ("手机号", "电话", "等下", "稍后", "后面", "再给", "信息")):
        return ""
    return cleaned


def _looks_like_group_passenger_count_context(text: str) -> bool:
    group_terms = ("团队", "团体", "公司", "集体", "多人", "一起", "一行", "参会", "团建")
    return any(term in text for term in group_terms)


REQUIRED_SOP_FIELDS: dict[str, dict[str, str]] = {
    "group_booking": {
        "route": "出发到达城市",
        "travel_time": "出行时间",
        "passenger_count": "出行人数",
    },
}


def _sanitize_collected(sop_id: str, collected: Mapping[str, Any]) -> dict[str, Any]:
    sanitized: dict[str, Any] = {}
    for key, value in collected.items():
        if _slot_value_is_unknown(value):
            continue
        if sop_id == "group_booking" and key == "route" and not _looks_like_complete_route(value):
            continue
        sanitized[str(key)] = value
    return sanitized


def _missing_required_fields(sop_id: str, collected: Mapping[str, Any]) -> tuple[str, ...]:
    labels = REQUIRED_SOP_FIELDS.get(sop_id)
    if not labels:
        return ()
    missing: list[str] = []
    for key, label in labels.items():
        value = collected.get(key)
        if _slot_value_is_unknown(value):
            missing.append(label)
            continue
        if key == "route" and not _looks_like_complete_route(value):
            missing.append(label)
    return tuple(missing)


def _missing_required_prompt(missing: tuple[str, ...]) -> str:
    return f"请补充 {', '.join(missing)}"


def _slot_value_is_unknown(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    if not text:
        return True
    unknown_terms = ("未定", "没定", "还没定", "待定", "等会", "稍后", "不确定", "再给", "未知")
    return any(term in text for term in unknown_terms)


def _looks_like_complete_route(value: Any) -> bool:
    text = str(value or "").strip()
    return bool(text) and any(separator in text for separator in ("到", "飞", "至", "去"))


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
    runtime_version: int = 1,
    runtime_refs: dict[str, Any] | None = None,
    runtime_status: str = "",
    fallback_reason: str = "",
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
        "runtimeVersion": runtime_version,
        "runtimeRefs": dict(runtime_refs or {}),
        "runtimeStatus": runtime_status,
        "fallbackReason": fallback_reason,
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


def _failure(
    request: SopExecutionRequest,
    code: str,
    message: str,
    *,
    runtime_code: str = "",
) -> SopExecutionResult:
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
    error = {"code": code, "message": message}
    if runtime_code:
        error["runtimeCode"] = runtime_code
    return SopExecutionResult(
        status=SopExecutionStatus.FAILED,
        current_step="",
        reply="",
        pending_prompt="",
        checkpoint=checkpoint,
        collected={},
        business_refs={},
        events=[],
        error=error,
    )


def _missing_chatflow_binding_failure(request: SopExecutionRequest) -> SopExecutionResult:
    error = missing_chatflow_binding_error(request.sop_id)
    return _failure(request, error["code"], error["message"])


def _is_missing_chatflow_error(exc: BizError) -> bool:
    return getattr(exc, "status_code", None) == 404 and "Chatflow not found" in str(exc)


def _with_prefixed_events(result: SopExecutionResult, events: list[dict[str, Any]]) -> SopExecutionResult:
    return SopExecutionResult(
        status=result.status,
        current_step=result.current_step,
        reply=result.reply,
        pending_prompt=result.pending_prompt,
        checkpoint=result.checkpoint,
        collected=dict(result.collected),
        business_refs=dict(result.business_refs),
        events=[*events, *[dict(event) for event in result.events]],
        error=result.error,
    )


def _project_events(run: Mapping[str, Any]) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    caller_context: dict[str, Any] = {}
    for event in _as_list(run.get("events")):
        if not isinstance(event, Mapping):
            continue
        payload = _as_mapping(event.get("payload"))
        event_type = str(event.get("type") or "")
        source = str(event.get("source") or "chatflow_runtime_v2")
        event_context = dict(payload.get("callerContext") or {})
        if event_context:
            caller_context = event_context
        observability = _as_mapping(event.get("observability"))
        correlation_refs = _as_mapping(observability.get("correlationRefs"))
        node_key = str(event.get("nodeId") or event.get("nodeKey") or correlation_refs.get("nodeKey") or "")
        node_run_id = _optional_int(payload.get("nodeRunId") or correlation_refs.get("nodeRunId"))
        projected = {
            "type": event_type,
            "source": source,
            "runtimeRunId": _int(event.get("runId")),
            "sourceEventId": _int(event.get("id")),
            "sourceSequence": _int(event.get("sequence")),
            "nodeKey": node_key,
            "callerContext": dict(caller_context),
            "event": {
                "id": _int(event.get("id")),
                "sequence": _int(event.get("sequence")),
                "type": event_type,
                "source": source,
            },
            "node": {
                "key": node_key,
                "type": str(payload.get("nodeType") or ""),
                "status": str(observability.get("nodeState") or _projected_node_state(event_type, payload)),
                "runId": node_run_id,
            },
        }
        checkpoint_id = event.get("checkpointId")
        if checkpoint_id is not None:
            projected["checkpointId"] = checkpoint_id
        events.append(projected)
    return events


def _async_pending_result(
    request: SopExecutionRequest,
    chatflow_id: int,
    invocation: Mapping[str, Any],
) -> SopExecutionResult:
    run_id = _int(invocation.get("runId"))
    raw_refs = invocation.get("runtimeRefs")
    runtime_refs = dict(raw_refs) if isinstance(raw_refs, Mapping) else _runtime_refs(invocation)
    runtime_status = str(invocation.get("status") or "RUNNING").upper() or "RUNNING"
    collected = _sanitize_collected(
        request.sop_id,
        {**request.collected, **_business_values_from_message(request.message)},
    )
    pending_prompt = "Chatflow SOP 正在后台执行，请稍候。"
    checkpoint = _checkpoint(
        request,
        chatflow_id=chatflow_id,
        run_id=run_id,
        event_id=None,
        checkpoint_id=None,
        session_id=str(invocation.get("sessionId") or ""),
        current_step="runtime_running",
        pending_prompt=pending_prompt,
        collected=collected,
        resume_mode="runtime-ref",
        runtime_version=2,
        runtime_refs=runtime_refs,
        runtime_status=runtime_status,
    )
    return SopExecutionResult(
        status=SopExecutionStatus.WAITING,
        current_step="runtime_running",
        reply=pending_prompt,
        pending_prompt=pending_prompt,
        checkpoint=checkpoint,
        collected=collected,
        business_refs=collected,
        events=[
            {
                "type": "chatflow_v2_async_started",
                "source": "chatflow_runtime_v2",
                "runtimeRunId": run_id,
                "runtimeStatus": runtime_status,
                "runtimeRefs": runtime_refs,
            }
        ],
        error=None,
    )


def _async_pending_result_from_checkpoint(
    request: SopExecutionRequest,
    chatflow_id: int,
    meta: Mapping[str, Any],
    latest: Mapping[str, Any],
) -> SopExecutionResult:
    run_id = _int(meta.get("runId") or latest.get("runId"))
    runtime_refs = dict(meta.get("runtimeRefs") or latest.get("runtimeRefs") or _runtime_refs({"runId": run_id}))
    return _async_pending_result(
        request,
        chatflow_id,
        {
            "runId": run_id,
            "sessionId": str(meta.get("sessionId") or latest.get("sessionId") or ""),
            "status": str(latest.get("status") or meta.get("runtimeStatus") or "RUNNING"),
            "runtimeRefs": runtime_refs,
        },
    )


def _v2_retryable_result_from_checkpoint(
    request: SopExecutionRequest,
    chatflow_id: int,
    meta: Mapping[str, Any],
    latest: Mapping[str, Any],
    *,
    reason: str,
) -> SopExecutionResult:
    run_id = _int(meta.get("runId") or latest.get("runId"))
    runtime_refs = dict(meta.get("runtimeRefs") or latest.get("runtimeRefs") or _runtime_refs({"runId": run_id}))
    collected = dict(request.checkpoint.collected) if request.checkpoint is not None else dict(request.collected)
    collected.update(_business_values_from_message(request.message))
    collected = _sanitize_collected(request.sop_id, collected)
    pending_prompt = "Chatflow SOP 正在同步 runtime 状态，请稍后重试。"
    current_step = request.checkpoint.current_node_id if request.checkpoint is not None else "runtime_retry"
    current_step = current_step or "runtime_retry"
    checkpoint = _checkpoint(
        request,
        chatflow_id=chatflow_id,
        run_id=run_id,
        event_id=_optional_int(meta.get("eventId")),
        checkpoint_id=_v2_checkpoint_id(latest) or _optional_int(meta.get("checkpointId")),
        session_id=str(meta.get("sessionId") or latest.get("sessionId") or ""),
        current_step=current_step,
        pending_prompt=pending_prompt,
        collected=collected,
        resume_mode="runtime-ref",
        runtime_version=2,
        runtime_refs=runtime_refs,
        runtime_status=str(latest.get("status") or meta.get("runtimeStatus") or "RETRYABLE"),
        fallback_reason=reason,
    )
    return SopExecutionResult(
        status=SopExecutionStatus.WAITING,
        current_step=current_step,
        reply=pending_prompt,
        pending_prompt=pending_prompt,
        checkpoint=checkpoint,
        collected=collected,
        business_refs=collected,
        events=[
            {
                "type": "chatflow_v2_retryable",
                "source": "chatflow_runtime_v2",
                "runtimeRunId": run_id,
                "runtimeStatus": str(latest.get("status") or meta.get("runtimeStatus") or "RETRYABLE"),
                "runtimeRefs": runtime_refs,
                "reason": reason,
            }
        ],
        error=None,
    )


def _v2_runtime_still_starting(latest: Mapping[str, Any]) -> bool:
    status = str(latest.get("status") or "").upper()
    return status in {"", "PENDING", "QUEUED", "RUNNING", "STARTED"}


def _v2_runtime_terminal(latest: Mapping[str, Any]) -> bool:
    status = str(latest.get("status") or "").upper()
    return status in {"SUCCEEDED", "FAILED", "CANCELLED"}


def _v2_runtime_failed(latest: Mapping[str, Any]) -> bool:
    status = str(latest.get("status") or "").upper()
    return status in {"FAILED", "CANCELLED"}


def _v2_failure_reason(latest: Mapping[str, Any]) -> str:
    error = latest.get("error")
    if error:
        return str(error)
    status = str(latest.get("status") or "").upper()
    return f"Runtime v2 run is {status or 'unavailable'}"


def _v2_bridge_settled(run: Mapping[str, Any], previous_checkpoint: SopCheckpoint) -> bool:
    status = str(run.get("status") or "").upper()
    if status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
        return True
    if status != "INTERRUPTED":
        return False
    previous_checkpoint_id = _optional_int(_chatflow_meta(previous_checkpoint).get("checkpointId"))
    current_checkpoint_id = _v2_checkpoint_id(run)
    if current_checkpoint_id is not None:
        return previous_checkpoint_id is None or current_checkpoint_id != previous_checkpoint_id
    previous_node = str(previous_checkpoint.current_node_id or previous_checkpoint.current_step or "")
    current_node = _v2_pending_node(run)
    return bool(current_node and previous_node and current_node != previous_node)


def _v2_runtime_result_run(latest: Mapping[str, Any], *, fallback: Mapping[str, Any]) -> dict[str, Any]:
    run = dict(latest)
    run_id = _int(run.get("runId") or fallback.get("runId"))
    run["runId"] = run_id
    run["status"] = str(run.get("status") or fallback.get("status") or "")
    run["sessionId"] = str(run.get("sessionId") or fallback.get("sessionId") or "")
    if not isinstance(run.get("events"), list):
        run["events"] = list(_as_list(fallback.get("events")))
    run["checkpointId"] = _v2_checkpoint_id(run)
    refs = run.get("runtimeRefs") if isinstance(run.get("runtimeRefs"), Mapping) else fallback.get("runtimeRefs")
    run["runtimeRefs"] = dict(refs) if isinstance(refs, Mapping) else _runtime_refs({"runId": run_id})
    return run


def _v2_checkpoint_id(run: Mapping[str, Any]) -> int | None:
    checkpoint = run.get("checkpoint")
    if isinstance(checkpoint, Mapping):
        checkpoint_id = _optional_int(checkpoint.get("id"))
        if checkpoint_id is not None:
            return checkpoint_id
    checkpoint_id = _optional_int(run.get("checkpointId"))
    if checkpoint_id is not None:
        return checkpoint_id
    return _event_checkpoint_id(run)


def _v2_pending_node(run: Mapping[str, Any]) -> str:
    checkpoint = run.get("checkpoint")
    if isinstance(checkpoint, Mapping):
        node_key = str(checkpoint.get("pendingNodeKey") or checkpoint.get("pending_node_key") or "")
        if node_key:
            return node_key
    return _pending_node(_as_mapping(run.get("output")), run)


def _run_from_v2_invocation(
    invocation: Mapping[str, Any],
    *,
    session_id: str = "",
    runtime_refs: dict[str, Any] | None = None,
) -> dict[str, Any]:
    result = invocation.get("result")
    run = dict(result) if isinstance(result, Mapping) else dict(invocation)
    run_id = _int(run.get("runId") or invocation.get("runId"))
    run["runId"] = run_id
    run["status"] = str(run.get("status") or invocation.get("status") or "")
    run["sessionId"] = session_id or str(run.get("sessionId") or invocation.get("sessionId") or "")
    event_page = invocation.get("events")
    events = _as_mapping(event_page).get("list") if isinstance(event_page, Mapping) else []
    run["events"] = events if isinstance(events, list) else []
    run["checkpointId"] = _checkpoint_id_from_result(run)
    refs = runtime_refs if runtime_refs is not None and runtime_refs else invocation.get("runtimeRefs")
    run["runtimeRefs"] = dict(refs) if isinstance(refs, Mapping) else _runtime_refs({"runId": run_id})
    return run


def _runtime_invocation_mode(mode: str) -> str:
    normalized = str(mode or "").strip().lower()
    if normalized in {"async", "stream", "stream-ref", "startandstreamref", "start_and_stream_ref"}:
        return "async"
    return "sync"


def _is_runtime_v2_compatibility_error(message: str) -> bool:
    return "Runtime V2 graph is not compatible" in message or "Unsupported runtime v2 graph" in message


def _runtime_refs(started: Mapping[str, Any]) -> dict[str, Any]:
    run_id = started.get("runId")
    return {
        "runId": run_id,
        "statusRef": started.get("statusRef") or f"/api/v1/runtime-runs/{run_id}",
        "eventsRef": started.get("eventsRef") or f"/api/v1/runtime-runs/{run_id}/events",
        "eventStreamRef": started.get("eventStreamRef")
        or f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
        "nodesRef": started.get("nodesRef") or f"/api/v1/runtime-runs/{run_id}/nodes",
        "resultRef": started.get("resultRef") or f"/api/v1/runtime-runs/{run_id}/result",
    }


def _projected_node_state(event_type: str, payload: Mapping[str, Any]) -> str:
    status = str(payload.get("status") or "").upper()
    if status:
        return status
    return {
        "workflow_node_started": "RUNNING",
        "workflow_node_completed": "COMPLETED",
        "workflow_node_failed": "FAILED",
        "workflow_node_waiting": "WAITING",
        "workflow_node_skipped": "SKIPPED",
        "handoff_requested": "WAITING",
    }.get(event_type, "")


def _checkpoint_id_from_result(run: Mapping[str, Any]) -> int | None:
    checkpoint = run.get("checkpoint")
    if isinstance(checkpoint, Mapping):
        return _optional_int(checkpoint.get("id"))
    return None


def _v2_idempotency_key(request: SopExecutionRequest) -> str:
    checkpoint_id = ""
    if request.checkpoint is not None:
        checkpoint_id = str(_chatflow_meta(request.checkpoint).get("checkpointId") or request.checkpoint.sop_runtime_id)
    return ":".join(
        [
            "chatflow-sop-v2",
            str(request.runtime_session_id),
            str(request.runtime_task_id or ""),
            request.sop_id,
            checkpoint_id,
            str(abs(hash(request.message))),
        ]
    )


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    parsed = _int(value)
    return parsed if parsed > 0 else None


def _runtime_version_is_v2(value: Any) -> bool:
    text = str(value or "").strip().lower()
    return text in {"2", "v2", "runtime_v2", "runtime-v2"}


def _as_mapping(value: Any) -> Mapping[str, Any]:
    if isinstance(value, Mapping):
        return cast(Mapping[str, Any], value)
    return {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
