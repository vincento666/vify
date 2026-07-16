from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import datetime
import hashlib
import json
from json import JSONDecodeError
import re
import time
from time import perf_counter
from typing import Any, Mapping

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.core.errors import BizError, ErrorCode
from app.core.responses import success
from app.modules.agent.infra.repository import AgentRepository
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.runtime_lab.domain.classifier import FakeConstrainedIntentClassifier, LlmConstrainedIntentClassifier
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.faq_gate import (
    CompositeFaqAnswerGate,
    FaqAnswerGate,
    FaqExactAnswerGate,
    FaqSemanticAnswerGate,
    RuntimeAirlineFaqGate,
)
from app.modules.runtime_lab.domain.payload import format_event, format_session, format_task
from app.modules.runtime_lab.domain.rag_gate import RagAnswerGate
from app.modules.runtime_lab.domain.aggregator import RuntimeLabBusinessContextAggregator
from app.modules.runtime_lab.domain.service import RuntimeLabService, _chatflow_meta_from_task
from app.modules.runtime_lab.domain.sop_adapter import MissingChatflowBindingAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.schemas import (
    RuntimeLabFallbackAgentRequest,
    RuntimeLabMessageRequest,
    RuntimeLabTemporaryModelTestRequest,
)
from app.modules.runtime_policy.domain.factories import (
    build_agent_output_policy_from_snapshot,
    build_classifier_from_snapshot,
    build_fallback_agent_from_snapshot,
)
from app.modules.runtime_policy.domain.resolver import RuntimePolicyResolveContext, RuntimePolicyResolver
from app.modules.runtime_policy.domain.service import RuntimeDecisionLogService
from app.modules.runtime_policy.domain.service import RuntimePolicyProfileService
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.web.schemas import RuntimePolicyProfileRequest
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.workflow.domain.runtime_invocation_gateway import RuntimeInvocationGateway
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.infra.realtime.redis_streams import RuntimeEventStreamBus
from app.modules.workflow.web.router import get_runtime_event_stream_bus, runtime_v2_stream_events

router = APIRouter(prefix="/api/v1/runtime-lab", tags=["runtime-lab"])

RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME = "034 RuntimeLab Airline Chatflow LLM Agent"


@dataclass(frozen=True)
class RuntimeLabRouteClassifierModel:
    model_id: str
    provider_type: str
    base_url: str
    auth_config: dict[str, Any]
    source: str
    model_config_id: int | None = None
    temperature: float | None = 0.0
    max_tokens: int | None = 360
    top_p: float | None = None


def get_runtime_lab_service(
    session: Session = Depends(get_session),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
) -> RuntimeLabService:
    settings = get_settings()
    effective_policy = RuntimePolicyResolver(RuntimePolicyRepository(session), settings).resolve()
    policy_snapshot = effective_policy["policySnapshot"]
    bindings = _runtime_lab_chatflow_bindings(settings.runtime_lab_sop_chatflow_ids)
    classifier = build_classifier_from_snapshot(policy_snapshot, settings)
    faq_answer_gate = _runtime_lab_faq_answer_gate(settings, session, policy_snapshot)
    faq_semantic_gate = _runtime_lab_faq_semantic_gate(settings, session, policy_snapshot)
    rag_answer_gate = _runtime_lab_rag_answer_gate(settings, session, policy_snapshot)
    fallback_agent = build_fallback_agent_from_snapshot(policy_snapshot, session=session)
    agent_output_policy = build_agent_output_policy_from_snapshot(policy_snapshot)
    policy_thresholds = (
        dict(policy_snapshot.get("thresholds") or {}) if effective_policy.get("source") == "profile" else {}
    )
    if not bindings:
        return RuntimeLabService(
            RuntimeLabRepository(session),
            adapter=MissingChatflowBindingAdapter(),
            classifier=classifier,
            faq_answer_gate=faq_answer_gate,
            faq_semantic_gate=faq_semantic_gate,
            rag_answer_gate=rag_answer_gate,
            fallback_agent=fallback_agent,
            agent_output_policy=agent_output_policy,
            policy_thresholds=policy_thresholds,
        )
    workflow_repository = WorkflowRepository(session)
    chatflow_state_repository = ChatflowStateRepository(session, event_stream_bus=event_stream_bus)
    workflow_service = WorkflowService(
        workflow_repository,
        flow_type="CHATFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        chatflow_state_repository=chatflow_state_repository,
        preferred_llm_agent_name=RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME,
    )
    runtime_v2_llm_service = WorkflowService(
        workflow_repository,
        flow_type="CHATFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        knowledge_facade=KnowledgeFacade(session),
        preferred_llm_agent_name=RUNTIME_LAB_AIRLINE_LLM_AGENT_NAME,
    )
    runtime_v2_service = ChatflowRuntimeV2Service(
        workflow_repository,
        chatflow_state_repository,
        knowledge_facade=KnowledgeFacade(session),
        llm_completer_resolver=(
            runtime_v2_llm_service.runtime_v2_llm_completer
            if _runtime_lab_sop_uses_live_llm(settings)
            else None
        ),
    )
    adapter = ChatflowSopRuntimeAdapter(
        workflow_service,
        sop_chatflow_ids=bindings,
        runtime_v2_service=runtime_v2_service,
        runtime_invocation_gateway=RuntimeInvocationGateway(
            runtime_v2_service,
            enqueue_background_run=_runtime_lab_background_enqueue(
                session,
                sop_llm_mode=settings.runtime_lab_sop_llm_mode,
            )
            if _runtime_invocation_uses_background(settings.runtime_lab_sop_runtime_invocation_mode)
            else None,
            enqueue_background_resume=_runtime_lab_background_resume_enqueue(
                session,
                sop_llm_mode=settings.runtime_lab_sop_llm_mode,
            )
            if _runtime_invocation_uses_background(settings.runtime_lab_sop_runtime_invocation_mode)
            else None,
        ),
        runtime_invocation_mode=settings.runtime_lab_sop_runtime_invocation_mode,
    )
    return RuntimeLabService(
        RuntimeLabRepository(session),
        adapter=adapter,
        classifier=classifier,
        faq_answer_gate=faq_answer_gate,
        faq_semantic_gate=faq_semantic_gate,
        rag_answer_gate=rag_answer_gate,
        fallback_agent=fallback_agent,
        agent_output_policy=agent_output_policy,
        policy_thresholds=policy_thresholds,
        current_step_runtime=runtime_v2_service,
    )


@router.post("/sessions")
def create_session(service: RuntimeLabService = Depends(get_runtime_lab_service)) -> dict[str, Any]:
    return success(format_session(service.create_session()))


@router.post("/messages")
def post_gateway_message(
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    runtime_session_id = request.session_id
    if runtime_session_id is None:
        runtime_session_id = int(service.create_session()["id"])
    return _post_runtime_lab_message(runtime_session_id, request, service, session, settings)


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return _post_runtime_lab_message(session_id, request, service, session, settings)


@router.post("/sessions/{session_id}/messages:stream")
def post_message_stream(
    session_id: int,
    request: RuntimeLabMessageRequest,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    heartbeat_ms: int = Query(default=250, alias="heartbeatMs", ge=100, le=30000),
    test_limit: int | None = Query(default=None, alias="_testLimit", ge=1, le=1000),
    test_heartbeat_limit: int | None = Query(
        default=None,
        alias="_testHeartbeatLimit",
        ge=1,
        le=1000,
    ),
    service: RuntimeLabService = Depends(get_runtime_lab_service),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    event_stream_bus: RuntimeEventStreamBus | None = Depends(get_runtime_event_stream_bus),
) -> StreamingResponse:
    pre_command_cursor = _runtime_lab_active_child_cursor(session, session_id)
    response, replayed = _post_runtime_lab_message_with_metadata(session_id, request, service, session, settings)
    payload = response.get("data")
    if not isinstance(payload, Mapping):
        payload = {}
    run_id = _runtime_lab_stream_run_id(payload)
    stream_after_sequence = _runtime_lab_stream_after_sequence(
        requested_after_sequence=after_sequence,
        pre_command_cursor=pre_command_cursor,
        run_id=run_id,
        replayed=replayed,
    )
    read_child_events = (
        _runtime_lab_child_event_reader(session, event_stream_bus) if run_id is not None else None
    )
    read_child_result = _runtime_lab_child_result_reader(session) if run_id is not None else None
    read_resume_job = _runtime_lab_resume_job_reader(session) if run_id is not None else None
    session.close()
    return StreamingResponse(
        _iter_runtime_lab_sop_sse(
            session_id=session_id,
            payload=dict(payload),
            run_id=run_id,
            after_sequence=stream_after_sequence,
            heartbeat_ms=heartbeat_ms,
            test_limit=test_limit,
            test_heartbeat_limit=test_heartbeat_limit,
            read_child_events=read_child_events,
            read_child_result=read_child_result,
            read_resume_job=read_resume_job,
        ),
        media_type="text/event-stream",
    )


def _post_runtime_lab_message(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService,
    session: Session,
    settings: Settings,
) -> dict[str, Any]:
    response, _replayed = _post_runtime_lab_message_with_metadata(session_id, request, service, session, settings)
    return response


def _post_runtime_lab_message_with_metadata(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService,
    session: Session,
    settings: Settings,
) -> tuple[dict[str, Any], bool]:
    effective_policy = RuntimePolicyResolver(RuntimePolicyRepository(session), settings).resolve()
    route_settings_signature = _runtime_lab_route_settings_signature(request.route_settings)
    result = service.handle_command(
        session_id,
        request.message,
        request.idempotency_key,
        enabled_sop_ids=request.enabled_sop_ids,
        policy_thresholds_override=_runtime_lab_route_settings_thresholds(request.route_settings),
        classifier_override=_runtime_lab_route_settings_classifier(request.route_settings, session),
        route_settings_signature=route_settings_signature,
    )
    if not result.replayed:
        RuntimeDecisionLogService(RuntimePolicyRepository(session)).record_message_decision(
            session_id=session_id,
            message_id=request.idempotency_key or "",
            user_message=request.message,
            command_payload=result.payload,
            effective_policy=effective_policy,
        )
    return success(result.payload), result.replayed


RuntimeLabChildEventReader = Callable[[int, int, int], list[dict[str, Any]]]
RuntimeLabChildResultReader = Callable[[int], dict[str, Any]]
RuntimeLabResumeJobReader = Callable[[int], dict[str, Any] | None]


def _runtime_lab_active_child_cursor(session: Session, session_id: int) -> tuple[int, int] | None:
    task = RuntimeLabRepository(session).get_active_task(session_id)
    if task is None:
        return None
    raw_run_id = task.get("chatflow_run_id")
    if isinstance(raw_run_id, bool) or not isinstance(raw_run_id, (int, str)):
        return None
    try:
        run_id = int(raw_run_id)
    except ValueError:
        return None
    run = WorkflowRepository(session).get_run(run_id)
    if run is None:
        return None
    events = ChatflowStateRepository(session).list_events(int(run["workflow_id"]), run_id)
    return run_id, max((_runtime_lab_event_sequence(event) for event in events), default=0)


def _runtime_lab_stream_after_sequence(
    *,
    requested_after_sequence: int,
    pre_command_cursor: tuple[int, int] | None,
    run_id: int | None,
    replayed: bool,
) -> int:
    if replayed or pre_command_cursor is None or run_id != pre_command_cursor[0]:
        return requested_after_sequence
    return max(requested_after_sequence, pre_command_cursor[1])


def _runtime_lab_stream_run_id(payload: Mapping[str, Any]) -> int | None:
    raw_run_id = payload.get("runId")
    if raw_run_id is None:
        active_task = payload.get("activeTask")
        if isinstance(active_task, Mapping):
            chatflow_session = active_task.get("chatflowSession")
            if isinstance(chatflow_session, Mapping):
                raw_run_id = chatflow_session.get("runId")
    if isinstance(raw_run_id, bool) or not isinstance(raw_run_id, (int, str)):
        return None
    try:
        run_id = int(raw_run_id)
    except ValueError:
        return None
    return run_id if run_id > 0 else None


def _runtime_lab_child_event_reader(
    session: Session,
    event_stream_bus: RuntimeEventStreamBus | None,
) -> RuntimeLabChildEventReader:
    bind = session.get_bind()
    if bind is None:
        raise RuntimeError("RuntimeLab child stream requires a database bind")
    factory = sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)

    def read(run_id: int, after_sequence: int, count: int) -> list[dict[str, Any]]:
        with factory() as stream_session:
            runtime_service = ChatflowRuntimeV2Service(
                WorkflowRepository(stream_session),
                ChatflowStateRepository(stream_session),
            )
            rows = runtime_v2_stream_events(
                runtime_service,
                event_stream_bus=event_stream_bus,
                run_id=run_id,
                after_sequence=after_sequence,
                heartbeat_ms=250,
                count=count,
            )
        return [dict(row) for row in rows if isinstance(row, Mapping)]

    return read


def _runtime_lab_child_result_reader(session: Session) -> RuntimeLabChildResultReader:
    bind = session.get_bind()
    if bind is None:
        raise RuntimeError("RuntimeLab child stream requires a database bind")
    factory = sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)

    def read(run_id: int) -> dict[str, Any]:
        with factory() as stream_session:
            runtime_service = ChatflowRuntimeV2Service(
                WorkflowRepository(stream_session),
                ChatflowStateRepository(stream_session),
            )
            return runtime_service.get_result(run_id)

    return read


def _runtime_lab_resume_job_reader(session: Session) -> RuntimeLabResumeJobReader:
    bind = session.get_bind()
    if bind is None:
        raise RuntimeError("RuntimeLab child stream requires a database bind")
    factory = sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)

    def read(job_id: int) -> dict[str, Any] | None:
        with factory() as stream_session:
            return RuntimeJobRepository(stream_session).get(job_id)

    return read


def _iter_runtime_lab_sop_sse(
    *,
    session_id: int,
    payload: dict[str, Any],
    run_id: int | None,
    after_sequence: int,
    heartbeat_ms: int,
    test_limit: int | None,
    test_heartbeat_limit: int | None,
    read_child_events: RuntimeLabChildEventReader | None,
    read_child_result: RuntimeLabChildResultReader | None,
    read_resume_job: RuntimeLabResumeJobReader | None = None,
) -> Iterable[str]:
    yield _runtime_lab_sse_data(
        {
            "type": "delta",
            "source": "runtime_lab",
            "sessionId": session_id,
            "runId": run_id,
            "payload": payload,
        }
    )
    if run_id is None or read_child_events is None:
        yield _runtime_lab_sse_data(
            {
                "type": "done",
                "source": "runtime_lab",
                "sessionId": session_id,
                "runId": run_id,
                "result": payload,
            }
        )
        return

    last_sequence = after_sequence
    emitted = 0
    heartbeats = 0
    while True:
        rows = read_child_events(run_id, last_sequence, test_limit or 100)
        if rows:
            for row in rows:
                sequence = _runtime_lab_event_sequence(row)
                if sequence <= last_sequence:
                    continue
                last_sequence = sequence
                if _runtime_lab_stale_resume_failure(row, read_resume_job):
                    continue
                frame = _runtime_lab_child_stream_frame(
                    session_id=session_id,
                    run_id=run_id,
                    sequence=sequence,
                    event=row,
                    result=payload,
                    runtime_result=(
                        read_child_result(run_id)
                        if _runtime_lab_terminal_stream_type(str(row.get("type") or row.get("eventType") or ""))
                        and read_child_result is not None
                        else None
                    ),
                )
                yield _runtime_lab_sse_data(frame)
                emitted += 1
                if frame["type"] in {"done", "error"}:
                    return
                if test_limit is not None and emitted >= test_limit:
                    return
            continue
        yield ": heartbeat\n\n"
        heartbeats += 1
        if test_heartbeat_limit is not None and heartbeats >= test_heartbeat_limit:
            return
        time.sleep(heartbeat_ms / 1000)


def _runtime_lab_child_stream_frame(
    *,
    session_id: int,
    run_id: int,
    sequence: int,
    event: Mapping[str, Any],
    result: dict[str, Any],
    runtime_result: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    event_type = str(event.get("type") or event.get("eventType") or "")
    event_payload = dict(event.get("payload") or {})
    terminal_type = _runtime_lab_terminal_stream_type(event_type)
    frame: dict[str, Any] = {
        "type": terminal_type or "delta",
        "source": "provider" if event_type == "llm_delta" and event_payload.get("streamSource") == "provider" else "runtime_v2",
        "sessionId": session_id,
        "runId": run_id,
        "sequence": sequence,
        "event": {
            "type": event_type,
            "nodeKey": event.get("nodeKey") or event.get("node_key"),
            "payload": event_payload,
        },
    }
    if frame["source"] == "provider":
        frame["delta"] = str(event_payload.get("content") or "")
    if terminal_type == "done":
        frame["result"] = _runtime_lab_terminal_projection(result, event, runtime_result)
    elif terminal_type == "error":
        frame["error"] = str((event.get("payload") or {}).get("error") or "Runtime V2 child run failed")
        failure = event_payload.get("failure")
        if not isinstance(failure, Mapping) and isinstance(runtime_result, Mapping):
            failure = runtime_result.get("failure")
        if isinstance(failure, Mapping):
            frame["failure"] = dict(failure)
    return frame


def _runtime_lab_stale_resume_failure(
    event: Mapping[str, Any],
    read_resume_job: RuntimeLabResumeJobReader | None,
) -> bool:
    if str(event.get("type") or event.get("eventType") or "") != "workflow_run_resume_failed":
        return False
    if read_resume_job is None:
        return False
    payload = _mapping_or_empty(event.get("payload"))
    raw_job_id = payload.get("jobId")
    raw_attempt_count = payload.get("attemptCount")
    if (
        isinstance(raw_job_id, bool)
        or isinstance(raw_attempt_count, bool)
        or not isinstance(raw_job_id, (int, str))
        or not isinstance(raw_attempt_count, (int, str))
    ):
        return False
    try:
        job_id = int(raw_job_id)
        attempt_count = int(raw_attempt_count)
    except ValueError:
        return False
    job = read_resume_job(job_id)
    return (
        job is None
        or str(job.get("status") or "").upper() != "FAILED"
        or int(job.get("attempt_count") or 0) != attempt_count
    )


def _runtime_lab_terminal_projection(
    initial_result: Mapping[str, Any],
    event: Mapping[str, Any],
    runtime_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    projected = dict(initial_result)
    durable_result = _mapping_or_empty(runtime_result)
    if durable_result:
        projected["runtimeResult"] = durable_result
        projected["status"] = str(durable_result.get("status") or projected.get("status") or "")
    output = _mapping_or_empty(durable_result.get("output"))
    if not output:
        event_payload = _mapping_or_empty(event.get("payload"))
        output = _mapping_or_empty(event_payload.get("output"))
    reply = _runtime_lab_terminal_reply(output)
    if reply:
        projected["reply"] = reply
        projected["answer"] = reply
    return projected


def _runtime_lab_terminal_reply(output: Mapping[str, Any]) -> str:
    interrupt = _mapping_or_empty(output.get("interrupt"))
    for value in (
        interrupt.get("question"),
        interrupt.get("prompt"),
        output.get("final"),
        output.get("answer"),
        output.get("content"),
        output.get("message"),
    ):
        if value is not None and str(value).strip():
            return str(value)
    return ""


def _mapping_or_empty(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _runtime_lab_terminal_stream_type(event_type: str) -> str | None:
    if event_type in {"workflow_run_completed", "workflow_run_interrupted"}:
        return "done"
    if event_type in {"workflow_run_failed", "workflow_run_cancelled", "workflow_run_resume_failed"}:
        return "error"
    return None


def _runtime_lab_event_sequence(event: Mapping[str, Any]) -> int:
    try:
        return int(event.get("sequence") or 0)
    except (TypeError, ValueError):
        return 0


def _runtime_lab_sse_data(payload: Mapping[str, Any]) -> str:
    return f"data: {json.dumps(dict(payload), ensure_ascii=False)}\n\n"


@router.post("/route-model/connectivity")
def test_route_model_connectivity(request: RuntimeLabTemporaryModelTestRequest) -> dict[str, Any]:
    started_at = perf_counter()
    model = _temporary_route_model(
        {
            "enabled": True,
            "model": request.model,
            "baseUrl": request.base_url,
            "apiKey": request.api_key,
            "temperature": request.temperature,
            "maxTokens": request.max_tokens,
            "topP": request.top_p,
            "providerType": request.provider_type,
        },
        source="runtime_lab_connectivity_test",
    )
    if model is None:
        raise BizError(ErrorCode.BAD_REQUEST, "Temporary route model config is required")
    builder = OpenAIChatRequestBuilder()
    payload = builder.build(
        model=model.model_id,
        messages=[ChatRequestMessage(role="user", content="1")],
        temperature=model.temperature,
        max_tokens=model.max_tokens,
        extra_params={"top_p": model.top_p} if model.top_p is not None else None,
    )
    try:
        response = _provider_client_from_model_config(model).complete(payload)
    except Exception as exc:  # noqa: BLE001 - returned to the lab UI as a diagnostic.
        return success(
            {
                "ok": False,
                "model": model.model_id,
                "elapsedMs": int((perf_counter() - started_at) * 1000),
                "error": _safe_connectivity_error(exc),
            }
        )
    return success(
        {
            "ok": True,
            "model": model.model_id,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
            "usage": _usage_from_response(response, payload, {}),
            "replyPreview": _connectivity_reply_preview(response),
        }
    )


@router.get("/sessions/{session_id}/tasks")
def list_tasks(
    session_id: int,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    tasks = service.list_tasks(session_id)
    return success({"list": [format_task(task) for task in tasks], "total": len(tasks)})


@router.get("/sessions/{session_id}/events")
def list_events(
    session_id: int,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    events = service.list_events(session_id)
    return success({"list": [format_event(event) for event in events], "total": len(events)})


@router.get("/sessions/{session_id}/chatflow-trace")
def get_chatflow_trace(
    session_id: int,
    session: Session = Depends(get_session),
) -> dict[str, Any]:
    return success(_runtime_lab_chatflow_trace(session_id, session))


@router.get("/config")
def get_config(
    tenant_id: str = Query("", alias="tenantId"),
    bot_id: str = Query("", alias="botId"),
    channel: str = "",
    session_id: str = Query("", alias="sessionId"),
    sop_group: str = Query("", alias="sopGroup"),
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    context = RuntimePolicyResolveContext(
        tenant_id=tenant_id,
        bot_id=bot_id,
        channel=channel,
        session_id=session_id,
        sop_group=sop_group,
    )
    return success(_runtime_lab_config(settings, session, context))


@router.put("/fallback-agent")
def update_fallback_agent(
    request: RuntimeLabFallbackAgentRequest,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    return success(_update_runtime_lab_fallback_agent(session, settings, request))


def _runtime_lab_chatflow_bindings(raw: str | None) -> dict[str, int]:
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except JSONDecodeError:
            return _runtime_lab_chatflow_bindings(text.strip("{}"))
        if not isinstance(parsed, dict):
            return {}
        return {str(key): int(value) for key, value in parsed.items() if str(key).strip()}
    bindings: dict[str, int] = {}
    for item in text.split(","):
        sop_id, _, chatflow_id = item.partition(":")
        if sop_id.strip() and chatflow_id.strip():
            bindings[sop_id.strip()] = int(chatflow_id.strip())
    return bindings


def _runtime_invocation_uses_background(mode: str) -> bool:
    return str(mode or "").strip().lower() in {
        "async",
        "stream",
        "stream-ref",
        "startandstreamref",
        "start_and_stream_ref",
    }


def _runtime_lab_sop_uses_live_llm(settings: Settings) -> bool:
    mode = str(settings.runtime_lab_sop_llm_mode or "mock").strip().lower()
    return mode not in {"mock", "fake", "deterministic", "off", "none"}


def _runtime_lab_background_enqueue(
    session: Session, *, sop_llm_mode: str
) -> Callable[[int, int], dict[str, Any]]:
    def enqueue(owner_id: int, run_id: int) -> dict[str, Any]:
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="CHATFLOW",
            owner_id=owner_id,
            payload={
                "runId": run_id,
                "ownerType": "CHATFLOW",
                "ownerId": owner_id,
                "idempotencyKey": "",
                "idempotencyLayer": "run",
                "source": "runtime_lab_sop_adapter",
                "sopLlmMode": sop_llm_mode,
            },
        )
        return {"jobId": int(job["id"]), "status": str(job["status"])}

    return enqueue


def _runtime_lab_background_resume_enqueue(
    session: Session, *, sop_llm_mode: str
) -> Callable[[int, int, int, dict[str, Any], str | None], dict[str, Any]]:
    def enqueue(
        owner_id: int,
        run_id: int,
        checkpoint_id: int,
        resume_data: dict[str, Any],
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        resume_key = str(idempotency_key or f"run-{run_id}-resume")
        job = RuntimeJobRepository(session).enqueue(
            run_id=run_id,
            owner_type="CHATFLOW",
            owner_id=owner_id,
            job_type=f"runtime_v2_resume:{checkpoint_id}",
            payload={
                "runId": run_id,
                "ownerType": "CHATFLOW",
                "ownerId": owner_id,
                "idempotencyKey": resume_key,
                "idempotencyLayer": "resume",
                "checkpointId": checkpoint_id,
                "resumeData": dict(resume_data),
                "source": "runtime_lab_sop_adapter",
                "sopLlmMode": sop_llm_mode,
            },
        )
        return {"jobId": int(job["id"]), "status": str(job["status"])}

    return enqueue


def _runtime_lab_config(
    settings: Settings,
    session: Session,
    context: RuntimePolicyResolveContext | None = None,
) -> dict[str, Any]:
    bindings = _runtime_lab_chatflow_bindings(settings.runtime_lab_sop_chatflow_ids)
    names = _chatflow_names(session, bindings.values())
    effective = RuntimePolicyResolver(RuntimePolicyRepository(session), settings).resolve(context)
    snapshot = effective["policySnapshot"]
    classifier = snapshot["classifier"]
    thresholds = dict(snapshot.get("thresholds") or {})
    fallback_agent = dict(snapshot.get("fallbackAgent") or {})
    fallback_agent_options = _runtime_lab_fallback_agent_options(session)
    fallback_agent_by_id = {int(agent["id"]): agent for agent in fallback_agent_options}
    fallback_agent_id = _optional_int_value(fallback_agent.get("agentId"))
    fallback_agent_row = fallback_agent_by_id.get(fallback_agent_id or 0)
    base_url = str(classifier.get("baseUrl") or "").strip()
    fallback_model = str(classifier.get("fallbackModel") or "").strip()
    api_key_configured = bool(str(classifier.get("apiKeyRef") or "").strip())
    mode = str(classifier.get("mode") or "fake").strip().lower()
    model = str(classifier.get("model") or "").strip()
    return {
        "policyProfile": {
            "source": effective["source"],
            "profileId": effective["profileId"],
            "profileVersion": effective["profileVersion"],
        },
        "sopBindings": [
            {
                "sopId": sop_id,
                "chatflowId": chatflow_id,
                "chatflowName": names.get(chatflow_id, ""),
                "exists": chatflow_id in names,
                "canvasPath": f"/chatflows/{chatflow_id}/canvas",
            }
            for sop_id, chatflow_id in bindings.items()
        ],
        "arbitrator": {
            "mode": mode,
            "model": model,
            "fallbackModel": fallback_model,
            "baseUrl": base_url,
            "apiKeyConfigured": api_key_configured,
            "available": (
                mode != "llm"
                or bool(base_url and model and api_key_configured)
            ),
        },
        "thresholds": thresholds,
        "faq": {
            "knowledgeBaseIds": list(snapshot["faq"].get("knowledgeBaseIds") or []),
            "exactEnabled": bool(snapshot["faq"].get("exactEnabled", True)),
            "semanticEnabled": bool(snapshot["faq"].get("semanticEnabled", True)),
            "topK": int(snapshot["faq"].get("topK") or 3),
            "rerank": bool(snapshot["faq"].get("rerank", False)),
        },
        "rag": {
            "knowledgeBaseIds": list(snapshot["rag"].get("knowledgeBaseIds") or []),
            "enabled": bool(snapshot["rag"].get("enabled", True)),
            "retrievalMode": str(snapshot["rag"].get("retrievalMode") or "hybrid"),
            "topK": int(snapshot["rag"].get("topK") or 5),
            "rerank": bool(snapshot["rag"].get("rerank", False)),
        },
        "handoff": {
            "enabled": bool(snapshot.get("handoff", {}).get("enabled", True)),
            "queue": str(snapshot.get("handoff", {}).get("queue") or "general"),
        },
        "fallbackAgent": {
            "enabled": bool(fallback_agent.get("enabled")),
            "type": str(fallback_agent.get("type") or "fake"),
            "agentId": fallback_agent_id,
            "agentName": str(fallback_agent_row.get("name") or "") if fallback_agent_row else "",
            "available": _runtime_lab_fallback_agent_available(fallback_agent, fallback_agent_row),
        },
        "fallbackAgentOptions": fallback_agent_options,
    }


def _update_runtime_lab_fallback_agent(
    session: Session,
    settings: Settings,
    request: RuntimeLabFallbackAgentRequest,
) -> dict[str, Any]:
    repository = RuntimePolicyRepository(session)
    if request.enabled:
        if request.agent_id is None:
            raise BizError(ErrorCode.BAD_REQUEST, "fallback Agent requires agentId")
        agent = AgentRepository(session).get(int(request.agent_id))
        if agent is None or not bool(agent.get("enabled")):
            raise BizError(ErrorCode.NOT_FOUND, "Fallback Agent not found or disabled")
    effective = RuntimePolicyResolver(repository, settings).resolve()
    snapshot = effective["policySnapshot"]
    fallback_agent = dict(snapshot.get("fallbackAgent") or {})
    if request.enabled:
        fallback_agent.update({"enabled": True, "type": "existing_agent", "agentId": int(request.agent_id)})
    else:
        fallback_agent.update({"enabled": False, "type": "fake", "agentId": None})

    service = RuntimePolicyProfileService(repository)
    if effective.get("source") == "profile" and effective.get("profileId"):
        row = repository.get_profile(int(effective["profileId"]))
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Runtime policy profile not found")
        payload = _runtime_policy_payload_from_row(row)
        payload["fallbackAgent"] = fallback_agent
        profile = service.update_profile(
            int(effective["profileId"]),
            RuntimePolicyProfileRequest.model_validate(payload),
        )
    else:
        payload = _runtime_policy_payload_from_snapshot(snapshot, fallback_agent)
        profile = service.create_profile(RuntimePolicyProfileRequest.model_validate(payload))
    selected_config = _runtime_lab_config(settings, session)
    selected_config["updatedProfile"] = {
        "profileId": profile["id"],
        "profileVersion": profile["version"],
    }
    return selected_config


def _runtime_lab_fallback_agent_options(session: Session) -> list[dict[str, Any]]:
    rows, _total = AgentRepository(session).list_page(1, 100, enabled=True)
    return [
        {
            "id": int(row["id"]),
            "name": str(row.get("name") or ""),
            "description": str(row.get("description") or ""),
            "enabled": bool(row.get("enabled")),
        }
        for row in rows
    ]


def _runtime_lab_fallback_agent_available(
    fallback_agent: Mapping[str, Any],
    agent_row: Mapping[str, Any] | None,
) -> bool:
    if not bool(fallback_agent.get("enabled")):
        return False
    fallback_type = str(fallback_agent.get("type") or "fake")
    if fallback_type == "fake":
        return True
    if fallback_type == "existing_agent":
        return agent_row is not None and bool(agent_row.get("enabled"))
    return False


def _runtime_lab_route_settings_thresholds(route_settings: Mapping[str, Any] | None) -> dict[str, Any]:
    if not route_settings:
        return {}
    thresholds = route_settings.get("thresholds")
    return dict(thresholds) if isinstance(thresholds, Mapping) else {}


def _runtime_lab_route_settings_signature(route_settings: Mapping[str, Any] | None) -> dict[str, Any]:
    if not route_settings:
        return {}
    signature: dict[str, Any] = {}
    thresholds = _runtime_lab_route_settings_thresholds(route_settings)
    if thresholds:
        signature["thresholds"] = thresholds
    arbitrator = route_settings.get("arbitrator")
    if isinstance(arbitrator, Mapping):
        signature["arbitrator"] = {
            "mode": str(arbitrator.get("mode") or "").strip().lower(),
            "modelConfigId": _optional_int_value(arbitrator.get("modelConfigId")),
            "fallbackModelConfigId": _optional_int_value(arbitrator.get("fallbackModelConfigId")),
            "temporaryModel": _temporary_model_signature(arbitrator.get("temporaryModel")),
            "temporaryFallbackModel": _temporary_model_signature(arbitrator.get("temporaryFallbackModel")),
        }
    return signature


def _runtime_lab_route_settings_classifier(
    route_settings: Mapping[str, Any] | None,
    session: Session,
) -> Any | None:
    if not route_settings:
        return None
    arbitrator = route_settings.get("arbitrator")
    if not isinstance(arbitrator, Mapping):
        return None
    mode = str(arbitrator.get("mode") or "").strip().lower()
    if mode == "fake":
        return FakeConstrainedIntentClassifier()
    if mode != "llm":
        return None
    primary_model = _temporary_route_model(arbitrator.get("temporaryModel"), source="runtime_lab_route_settings_temporary")
    model_facade = ProviderModelFacade(session)
    if primary_model is None:
        model_config_id = _optional_int_value(arbitrator.get("modelConfigId"))
        if model_config_id is None:
            return None
        primary_model = _route_model_from_model_config(model_facade.get_enabled_model_config(model_config_id))

    fallback_model = _temporary_route_model(
        arbitrator.get("temporaryFallbackModel"),
        source="runtime_lab_route_settings_temporary_fallback",
    )
    fallback_model_config_id = _optional_int_value(arbitrator.get("fallbackModelConfigId"))
    if fallback_model is None and fallback_model_config_id is not None and fallback_model_config_id != primary_model.model_config_id:
        fallback_model = _route_model_from_model_config(model_facade.get_enabled_model_config(fallback_model_config_id))
    return _runtime_lab_classifier_from_route_model(primary_model, fallback_model=fallback_model)


def _runtime_lab_classifier_from_route_model(
    model_config: RuntimeLabRouteClassifierModel,
    *,
    fallback_model: RuntimeLabRouteClassifierModel | None = None,
) -> LlmConstrainedIntentClassifier:
    builder = OpenAIChatRequestBuilder()
    client = _provider_client_from_model_config(model_config)
    fallback_client = _provider_client_from_model_config(fallback_model) if fallback_model is not None else None

    def complete(classifier_payload: dict[str, Any]) -> dict[str, Any]:
        llm_payload = _route_classifier_payload(builder, model_config, classifier_payload)
        started_at = perf_counter()
        actual_model = model_config
        try:
            response = client.complete(llm_payload)
        except Exception:
            if fallback_model is None or fallback_client is None:
                raise
            fallback_payload = _route_classifier_payload(builder, fallback_model, classifier_payload)
            actual_model = fallback_model
            llm_payload = fallback_payload
            response = fallback_client.complete(fallback_payload)
        parsed = _parse_llm_classifier_response(response)
        parsed_output = dict(parsed)
        parsed["_debug"] = {
            "model": actual_model.model_id,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
            "input": _redact_llm_payload(llm_payload),
            "output": parsed_output,
            "usage": _usage_from_response(response, llm_payload, parsed_output),
            "source": actual_model.source,
            "modelConfigId": actual_model.model_config_id,
            "fallbackModelConfigId": fallback_model.model_config_id if fallback_model is not None else None,
        }
        return parsed

    return LlmConstrainedIntentClassifier(complete)


def _route_classifier_payload(
    builder: OpenAIChatRequestBuilder,
    model_config: RuntimeLabRouteClassifierModel,
    classifier_payload: dict[str, Any],
) -> dict[str, Any]:
    extra_params: dict[str, Any] = {
        "response_format": {"type": "json_object"},
        "reasoning": {"effort": "none", "exclude": True},
    }
    if model_config.top_p is not None:
        extra_params["top_p"] = model_config.top_p
    return builder.build(
        model=str(model_config.model_id),
        messages=[
            ChatRequestMessage(
                role="system",
                content=(
                    "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择，"
                    "返回 JSON 对象：selected_action, selected_candidate_id, confidence, rationale, "
                    "needs_clarification, clarification_question。不要创造候选。"
                ),
            ),
            ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
        ],
        temperature=model_config.temperature,
        max_tokens=model_config.max_tokens,
        extra_params=extra_params,
    )


def _route_model_from_model_config(model_config: Any) -> RuntimeLabRouteClassifierModel:
    return RuntimeLabRouteClassifierModel(
        model_id=str(model_config.model_id),
        provider_type=str(model_config.provider_type),
        base_url=str(model_config.provider_base_url),
        auth_config=dict(model_config.provider_auth_config or {}),
        model_config_id=int(model_config.id),
        source="runtime_lab_route_settings",
    )


def _temporary_route_model(value: Any, *, source: str) -> RuntimeLabRouteClassifierModel | None:
    if not isinstance(value, Mapping):
        return None
    if value.get("enabled") is False:
        return None
    model_id = str(value.get("model") or value.get("modelId") or "").strip()
    base_url = str(value.get("baseUrl") or value.get("base_url") or "").strip()
    api_key = str(value.get("apiKey") or value.get("api_key") or "").strip()
    if not model_id and not base_url and not api_key:
        return None
    if not model_id:
        raise BizError(ErrorCode.BAD_REQUEST, "Temporary route model requires model")
    if not base_url:
        raise BizError(ErrorCode.BAD_REQUEST, "Temporary route model requires baseUrl")
    if not api_key and not base_url.startswith("mock://"):
        raise BizError(ErrorCode.BAD_REQUEST, "Temporary route model requires apiKey")
    return RuntimeLabRouteClassifierModel(
        model_id=model_id,
        provider_type=str(value.get("providerType") or "OPENAI_COMPATIBLE"),
        base_url=base_url,
        auth_config={"api_key": api_key} if api_key else {},
        source=source,
        temperature=_optional_float_value(value.get("temperature"), default=0.0, minimum=0.0, maximum=2.0),
        max_tokens=_optional_int_range(value.get("maxTokens") or value.get("max_tokens"), default=360, minimum=1, maximum=8192),
        top_p=_optional_float_value(value.get("topP") or value.get("top_p"), default=None, minimum=0.0, maximum=1.0),
    )


def _temporary_model_signature(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, Mapping):
        return None
    api_key = str(value.get("apiKey") or value.get("api_key") or "").strip()
    return {
        "enabled": value.get("enabled") is not False,
        "model": str(value.get("model") or value.get("modelId") or "").strip(),
        "baseUrl": str(value.get("baseUrl") or value.get("base_url") or "").strip(),
        "apiKeyHash": hashlib.sha256(api_key.encode("utf-8")).hexdigest() if api_key else "",
        "temperature": value.get("temperature"),
        "maxTokens": value.get("maxTokens") or value.get("max_tokens"),
        "topP": value.get("topP") or value.get("top_p"),
    }


def _connectivity_reply_preview(response: Mapping[str, Any]) -> str:
    choices = response.get("choices")
    if isinstance(choices, list) and choices:
        first = choices[0]
        if isinstance(first, Mapping):
            message = first.get("message")
            if isinstance(message, Mapping):
                return str(message.get("content") or "")[:200]
            return str(first.get("text") or "")[:200]
    return ""


def _safe_connectivity_error(exc: Exception) -> str:
    text = str(exc) or exc.__class__.__name__
    text = re.sub(r"sk-[A-Za-z0-9_\\-]{8,}", "sk-***", text)
    text = re.sub(r"sk-or-[A-Za-z0-9_\\-]{8,}", "sk-or-***", text)
    return text[:500]


def _provider_client_from_model_config(model_config: RuntimeLabRouteClassifierModel | None) -> ProviderBackedOpenAIChatClient:
    if model_config is None:
        raise BizError(ErrorCode.BAD_REQUEST, "Runtime route model config is required")
    return ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type=model_config.provider_type,
            base_url=model_config.base_url,
            auth_config=dict(model_config.auth_config),
        ),
        timeout=90.0,
        max_attempts=3,
        retry_sleep=2.0,
    )


def _runtime_policy_payload_from_row(row: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "name": str(row.get("name") or "RuntimeLab routing policy"),
        "description": str(row.get("description") or ""),
        "status": str(row.get("status") or "active"),
        "mode": str(row.get("mode") or "balanced"),
        "bindings": dict(row.get("bindings") or {}),
        "thresholds": dict(row.get("thresholds") or {}),
        "classifier": dict(row.get("classifier") or {}),
        "faq": dict(row.get("faq") or {}),
        "rag": dict(row.get("rag") or {}),
        "fallbackAgent": dict(row.get("fallback_agent") or {}),
        "handoff": dict(row.get("handoff") or {}),
        "audit": dict(row.get("audit") or {}),
    }


def _runtime_policy_payload_from_snapshot(
    snapshot: Mapping[str, Any],
    fallback_agent: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "name": "034 RuntimeLab routing policy",
        "description": "RuntimeLab generated policy for unified routing fallback Agent selection",
        "status": "active",
        "mode": str(snapshot.get("mode") or "balanced"),
        "bindings": dict(snapshot.get("bindings") or {}),
        "thresholds": dict(snapshot.get("thresholds") or {}),
        "classifier": _runtime_policy_schema_safe_classifier(snapshot.get("classifier")),
        "faq": dict(snapshot.get("faq") or {}),
        "rag": dict(snapshot.get("rag") or {}),
        "fallbackAgent": dict(fallback_agent),
        "handoff": dict(snapshot.get("handoff") or {}),
        "audit": {
            "createdBy": "runtime-lab",
            "updatedBy": "runtime-lab",
            "changeReason": "Select RuntimeLab fallback Agent",
        },
    }


def _runtime_policy_schema_safe_classifier(value: Any) -> dict[str, Any]:
    classifier = dict(value or {})
    if str(classifier.get("mode") or "").lower() != "llm":
        return classifier
    required = (
        str(classifier.get("baseUrl") or "").strip(),
        str(classifier.get("apiKeyRef") or "").strip(),
        str(classifier.get("model") or "").strip(),
    )
    if all(required):
        return classifier
    classifier["enabled"] = False
    return classifier


def _runtime_lab_faq_answer_gate(
    settings: Settings,
    session: Session,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> FaqAnswerGate | None:
    faq_config = _runtime_policy_faq_config(settings, policy_snapshot)
    if not bool(faq_config.get("exactEnabled", True)):
        return None
    runtime_faq_gate = RuntimeAirlineFaqGate()
    knowledge_base_ids = _runtime_lab_id_list(faq_config.get("knowledgeBaseIds"))
    if not knowledge_base_ids:
        return runtime_faq_gate
    thresholds = dict((policy_snapshot or {}).get("thresholds") or {})
    return CompositeFaqAnswerGate(
        (
            runtime_faq_gate,
            FaqExactAnswerGate(
                KnowledgeFacade(session),
                knowledge_base_ids=knowledge_base_ids,
                top_k=int(faq_config.get("topK") or 3),
                keyword_min_score=_runtime_lab_threshold(thresholds, "faqKeywordMinScore", 0.0),
                keyword_min_margin=_runtime_lab_threshold(thresholds, "faqKeywordMinMargin", 0.0),
            ),
        )
    )


def _runtime_lab_faq_semantic_gate(
    settings: Settings,
    session: Session,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> FaqSemanticAnswerGate | None:
    faq_config = _runtime_policy_faq_config(settings, policy_snapshot)
    if not bool(faq_config.get("semanticEnabled", True)):
        return None
    knowledge_base_ids = _runtime_lab_id_list(faq_config.get("knowledgeBaseIds"))
    if not knowledge_base_ids:
        return None
    thresholds = dict((policy_snapshot or {}).get("thresholds") or {})
    return FaqSemanticAnswerGate(
        KnowledgeFacade(session),
        knowledge_base_ids=knowledge_base_ids,
        top_k=int(faq_config.get("topK") or 5),
        rerank=bool(faq_config.get("rerank", True)),
        min_score=_runtime_lab_threshold(thresholds, "faqSemanticMinScore", 0.85),
        min_margin=_runtime_lab_threshold(thresholds, "faqSemanticMinMargin", 0.12),
    )


def _runtime_lab_rag_answer_gate(
    settings: Settings,
    session: Session,
    policy_snapshot: Mapping[str, Any] | None = None,
) -> RagAnswerGate | None:
    rag_config = _runtime_policy_rag_config(settings, policy_snapshot)
    if not bool(rag_config.get("enabled", True)):
        return None
    knowledge_base_ids = _runtime_lab_id_list(rag_config.get("knowledgeBaseIds"))
    if not knowledge_base_ids:
        return None
    thresholds = dict((policy_snapshot or {}).get("thresholds") or {})
    return RagAnswerGate(
        KnowledgeFacade(session),
        knowledge_base_ids=knowledge_base_ids,
        top_k=int(rag_config.get("topK") or 3),
        retrieval_mode=str(rag_config.get("retrievalMode") or "hybrid"),
        rerank=bool(rag_config.get("rerank", True)),
        min_score=_runtime_lab_threshold(thresholds, "ragMinScore", 0.7),
        lexical_accept_threshold=_runtime_lab_threshold(thresholds, "ragLexicalAcceptThreshold", 0.6),
    )


def _runtime_policy_faq_config(settings: Settings, policy_snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    if policy_snapshot and isinstance(policy_snapshot.get("faq"), Mapping):
        return dict(policy_snapshot["faq"])
    return {
        "knowledgeBaseIds": _runtime_lab_id_list(settings.runtime_lab_faq_knowledge_base_ids),
        "exactEnabled": True,
        "semanticEnabled": True,
        "topK": 3,
        "rerank": False,
    }


def _runtime_policy_rag_config(settings: Settings, policy_snapshot: Mapping[str, Any] | None) -> dict[str, Any]:
    if policy_snapshot and isinstance(policy_snapshot.get("rag"), Mapping):
        return dict(policy_snapshot["rag"])
    return {
        "enabled": True,
        "knowledgeBaseIds": _runtime_lab_id_list(settings.runtime_lab_rag_knowledge_base_ids),
        "retrievalMode": "hybrid",
        "topK": 3,
        "rerank": True,
    }


def _runtime_lab_id_list(raw: Any) -> list[int]:
    if isinstance(raw, (list, tuple)):
        values = raw
    else:
        text = (raw or "").strip()
        if not text:
            return []
        values = text.split(",")
    ids: list[int] = []
    for item in values:
        try:
            ids.append(int(str(item).strip()))
        except ValueError:
            continue
    return ids


def _runtime_lab_threshold(thresholds: Mapping[str, Any], key: str, default: float) -> float:
    raw = thresholds.get(key, default)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


def _chatflow_names(session: Session, chatflow_ids: Any) -> dict[int, str]:
    ids = [int(chatflow_id) for chatflow_id in chatflow_ids]
    if not ids:
        return {}
    workflow = Base.metadata.tables["workflow"]
    rows = session.execute(
        workflow.select().where(
            workflow.c.id.in_(ids),
            workflow.c.flow_type == "CHATFLOW",
            workflow.c.deleted.is_(False),
        )
    ).mappings().all()
    return {int(row["id"]): str(row["name"]) for row in rows}


def _runtime_lab_chatflow_trace(session_id: int, session: Session) -> dict[str, Any]:
    runtime_repository = RuntimeLabRepository(session)
    if runtime_repository.get_session(session_id) is None:
        raise BizError(ErrorCode.NOT_FOUND, "Runtime lab session not found")
    workflow_repository = WorkflowRepository(session)
    state_repository = ChatflowStateRepository(session)
    # Business context comes from the aggregator projection (chatflow
    # ``conversation`` scope + regex-derived refs), replacing the banned
    # checkpoint.collected / task.business_refs reads (slice 213.3.5f).
    workflow_service = WorkflowService(
        workflow_repository,
        flow_type="CHATFLOW",
        chatflow_state_repository=state_repository,
    )
    aggregator = RuntimeLabBusinessContextAggregator(runtime_repository, workflow_service)
    business_refs = aggregator.collect(session_id)
    ledger_events = [
        _format_runtime_lab_ledger_event(event)
        for event in runtime_repository.list_events(session_id)
    ]
    traces = [
        _runtime_task_chatflow_trace(
            task,
            workflow_repository,
            state_repository,
            business_refs,
            ledger_events,
        )
        for task in runtime_repository.list_tasks(session_id)
    ]
    return {"tasks": traces, "total": len(traces)}


def _runtime_task_chatflow_trace(
    task: dict[str, Any],
    workflow_repository: WorkflowRepository,
    state_repository: ChatflowStateRepository,
    business_refs: dict[str, Any],
    ledger_events: list[dict[str, Any]],
) -> dict[str, Any]:
    # chatflow meta is sourced from the task's first-class ``chatflow_*`` ref
    # columns (slice 213.3.1), not checkpoint.scoped_variables.__chatflow.
    meta = _chatflow_meta_from_task(task)
    chatflow_id = _int_value(meta.get("chatflowId"))
    run_id = _int_value(meta.get("runId"))
    workflow = workflow_repository.get(chatflow_id, flow_type="CHATFLOW") if chatflow_id > 0 else None
    node_rows = workflow_repository.list_nodes(chatflow_id) if workflow is not None else []
    edge_rows = workflow_repository.list_edges(chatflow_id) if workflow is not None else []
    node_runs = workflow_repository.list_node_runs(run_id) if run_id > 0 else []
    node_runs_by_key = _latest_node_runs_by_key(node_runs)
    run = workflow_repository.get_run(run_id) if run_id > 0 else None
    waiting_checkpoint = (
        state_repository.get_waiting_checkpoint(chatflow_id, run_id) if chatflow_id > 0 and run_id > 0 else None
    )
    raw_events = (
        state_repository.list_events(chatflow_id, run_id) if chatflow_id > 0 and run_id > 0 else []
    )
    # current_step comes from the durable runtime-v2 waiting checkpoint
    # (``pending_node_key``), not the banned ``checkpoint.current_step``.
    current_step = str(waiting_checkpoint.get("pending_node_key") or "") if waiting_checkpoint else ""
    # The chatflow session id is a string; the BIGINT task ref column cannot
    # carry it, so derive it from the durable runtime state (waiting checkpoint
    # or run events) keyed by run_id, not checkpoint.scoped_variables.__chatflow.
    chatflow_session_id = _trace_chatflow_session_id(waiting_checkpoint, raw_events)
    events = [_format_runtime_chatflow_event(event) for event in raw_events]
    session_variables = _chatflow_session_variables(state_repository, chatflow_id, chatflow_session_id)
    runtime_refs = _chatflow_runtime_refs(meta, run_id)
    pending_prompt = _trace_pending_prompt(waiting_checkpoint, raw_events, session_variables)
    checkpoint = _format_trace_checkpoint(waiting_checkpoint)
    scoped_variables = _trace_scoped_variables(waiting_checkpoint)

    return {
        "taskId": int(task["id"]),
        "sopId": task["sop_id"],
        "status": task["status"],
        "runStatus": str(run.get("status") or "") if run else "",
        "currentStep": current_step,
        "pendingPrompt": pending_prompt,
        "checkpoint": checkpoint,
        "chatflow": {
            "chatflowId": chatflow_id or None,
            "chatflowName": str(workflow.get("name") or "") if workflow else "",
            "exists": workflow is not None,
            "runId": run_id or None,
            "eventId": _optional_int_value(meta.get("eventId")),
            "checkpointId": _optional_int_value(meta.get("checkpointId")),
            "sessionId": chatflow_session_id,
            **runtime_refs,
            "canvasPath": f"/chatflows/{chatflow_id}/canvas" if chatflow_id > 0 else "",
            "debugPath": f"/chatflows/{chatflow_id}/canvas?runId={run_id}&debug=1"
            if chatflow_id > 0 and run_id > 0
            else "",
        },
        "nodes": [
            _runtime_trace_node(node, node_runs_by_key.get(str(node["node_key"])), current_step, str(task["status"]))
            for node in node_rows
        ],
        "edges": [
            {
                "sourceNodeKey": edge["source_node_key"],
                "targetNodeKey": edge["target_node_key"],
                "condition": edge.get("condition_expr"),
            }
            for edge in edge_rows
        ],
        "events": events,
        "nodeEvents": events,
        "ledgerEvents": ledger_events,
        "variables": {
            "businessRefs": business_refs,
            "collected": business_refs,
            "scoped": scoped_variables,
            "scopedVariables": scoped_variables,
            "session": session_variables,
        },
    }


def _format_runtime_lab_ledger_event(row: dict[str, Any]) -> dict[str, Any]:
    event = format_event(row)
    payload = event.get("payload")
    if isinstance(payload, Mapping):
        event["payload"] = {
            str(key): value
            for key, value in payload.items()
            if str(key)
            not in {
                "currentStep",
                "pendingPrompt",
                "collected",
                "scopedVariables",
                "checkpoint",
                "checkpointId",
                "nodeEvents",
                "runStatus",
                "businessRefs",
            }
        }
    return event


def _trace_pending_prompt(
    waiting_checkpoint: dict[str, Any] | None,
    raw_events: list[dict[str, Any]],
    session_variables: dict[str, Any],
) -> str:
    node_key = str((waiting_checkpoint or {}).get("pending_node_key") or "")
    for event in reversed(raw_events):
        if node_key and str(event.get("node_key") or "") not in {"", node_key}:
            continue
        payload = event.get("payload") if isinstance(event.get("payload"), Mapping) else {}
        for key in ("question", "prompt", "followup"):
            value = payload.get(key) if isinstance(payload, Mapping) else None
            if value:
                return str(value)
    node_outputs = session_variables.get("node_outputs")
    if isinstance(node_outputs, Mapping) and node_key:
        node_output = node_outputs.get(node_key)
        if isinstance(node_output, Mapping):
            for key in ("question", "prompt", "followup"):
                value = node_output.get(key)
                if value:
                    return str(value)
    resume_schema = (waiting_checkpoint or {}).get("resume_schema")
    if isinstance(resume_schema, Mapping):
        for key in ("question", "prompt", "title"):
            value = resume_schema.get(key)
            if value:
                return str(value)
    return ""


def _format_trace_checkpoint(checkpoint: dict[str, Any] | None) -> dict[str, Any] | None:
    if checkpoint is None:
        return None
    return {
        "id": int(checkpoint["id"]),
        "eventId": int(checkpoint["event_id"]) if checkpoint.get("event_id") else None,
        "pendingNodeKey": str(checkpoint["pending_node_key"]),
        "resumeSchema": dict(checkpoint.get("resume_schema") or {}),
        "status": str(checkpoint["status"]),
        "nodeOutputs": dict(checkpoint.get("node_outputs") or {}),
        "variableScopes": dict(checkpoint.get("variable_scopes") or {}),
        "expiresAt": _format_datetime(checkpoint.get("expires_at")),
    }


def _trace_scoped_variables(checkpoint: dict[str, Any] | None) -> dict[str, Any]:
    if checkpoint is None:
        return {}
    variable_scopes = checkpoint.get("variable_scopes")
    if not isinstance(variable_scopes, Mapping):
        return {}
    flattened: dict[str, Any] = {}
    for scope, values in variable_scopes.items():
        if isinstance(values, Mapping):
            for key, value in values.items():
                flattened[f"{scope}.{key}"] = value
        else:
            flattened[str(scope)] = values
    return flattened


def _trace_chatflow_session_id(
    waiting_checkpoint: dict[str, Any] | None,
    raw_events: list[dict[str, Any]],
) -> str:
    """Derive the chatflow session id (a string) from durable runtime state.

    The task's ``chatflow_session_id`` ref column is a BIGINT and cannot carry
    the string session id, so the chatflow-trace projection reads it from the
    runtime-v2 waiting checkpoint or run events (keyed by run_id) instead of
    ``checkpoint.scoped_variables.__chatflow`` (slice 213.3.5f).
    """
    if waiting_checkpoint and waiting_checkpoint.get("session_id"):
        return str(waiting_checkpoint["session_id"])
    for event in raw_events:
        session_id = event.get("session_id")
        if session_id:
            return str(session_id)
    return ""


def _chatflow_runtime_refs(meta: Mapping[str, Any], run_id: int) -> dict[str, str]:
    if run_id <= 0:
        return {}
    raw_refs = meta.get("runtimeRefs")
    refs = dict(raw_refs) if isinstance(raw_refs, Mapping) else {}
    return {
        "statusRef": str(refs.get("statusRef") or f"/api/v1/runtime-runs/{run_id}"),
        "eventsRef": str(refs.get("eventsRef") or f"/api/v1/runtime-runs/{run_id}/events"),
        "eventStreamRef": str(
            refs.get("eventStreamRef") or f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0"
        ),
        "nodesRef": str(refs.get("nodesRef") or f"/api/v1/runtime-runs/{run_id}/nodes"),
        "resultRef": str(refs.get("resultRef") or f"/api/v1/runtime-runs/{run_id}/result"),
    }


def _latest_node_runs_by_key(node_runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for node_run in node_runs:
        result[str(node_run.get("node_key") or "")] = node_run
    return result


def _runtime_trace_node(
    node: dict[str, Any],
    node_run: dict[str, Any] | None,
    current_step: str,
    task_status: str,
) -> dict[str, Any]:
    node_key = str(node["node_key"])
    current = node_key == current_step
    return {
        "nodeKey": node_key,
        "nodeType": node["type"],
        "name": node.get("name") or node_key,
        "status": _runtime_node_status(node_run, current=current, task_status=task_status),
        "current": current,
        "elapsedMs": int(node_run.get("elapsed_ms") or 0) if node_run else 0,
        "inputs": (node_run.get("inputs") or {}) if node_run else {},
        "outputs": (node_run.get("outputs") or {}) if node_run else {},
        "usage": _node_usage(node, node_run),
        "error": str(node_run.get("error") or "") if node_run else "",
    }


def _node_usage(node: dict[str, Any], node_run: dict[str, Any] | None) -> dict[str, Any]:
    if node_run is None:
        return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False}
    outputs = node_run.get("outputs") if isinstance(node_run.get("outputs"), Mapping) else {}
    usage = outputs.get("__usage") if isinstance(outputs.get("__usage"), Mapping) else {}
    if usage:
        return {
            "inputTokens": _int_value(usage.get("inputTokens")),
            "outputTokens": _int_value(usage.get("outputTokens")),
            "totalTokens": _int_value(usage.get("totalTokens")),
            "estimated": bool(usage.get("estimated", False)),
        }
    if str(node.get("type") or "").upper() == "LLM":
        return {
            "inputTokens": _estimate_tokens(node_run.get("inputs") or {}),
            "outputTokens": _estimate_tokens(outputs),
            "totalTokens": _estimate_tokens(node_run.get("inputs") or {}) + _estimate_tokens(outputs),
            "estimated": True,
        }
    return {"inputTokens": 0, "outputTokens": 0, "totalTokens": 0, "estimated": False}


def _runtime_node_status(node_run: dict[str, Any] | None, *, current: bool, task_status: str) -> str:
    raw = str(node_run.get("status") or "") if node_run else ""
    if current and task_status in {"RUNNING", "WAITING"}:
        if raw in {"", "INTERRUPTED"}:
            return "WAITING"
        if raw == "RUNNING":
            return "RUNNING"
    return raw or "PENDING"


def _chatflow_session_variables(
    state_repository: ChatflowStateRepository,
    chatflow_id: int,
    session_id: str,
) -> dict[str, Any]:
    if chatflow_id <= 0 or not session_id:
        return {}
    state = state_repository.get_session(chatflow_id, session_id)
    if state is None:
        return {}
    variables = state.get("variables")
    return dict(variables) if isinstance(variables, Mapping) else {}


def _format_runtime_chatflow_event(event: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(event["id"]),
        "type": event["event_type"],
        "runId": int(event["run_id"]),
        "sequence": int(event["sequence"]),
        "nodeKey": event["node_key"],
        "payload": event["payload"] or {},
        "checkpointId": int(event["checkpoint_id"]) if event.get("checkpoint_id") else None,
        "createdAt": _format_datetime(event.get("created_at")),
    }


def _int_value(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int_value(value: Any) -> int | None:
    parsed = _int_value(value)
    return parsed if parsed > 0 else None


def _optional_int_range(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _optional_float_value(
    value: Any,
    *,
    default: float | None,
    minimum: float,
    maximum: float,
) -> float | None:
    if value is None or value == "":
        return default
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


def _format_datetime(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _runtime_lab_intent_classifier(settings: Settings) -> LlmConstrainedIntentClassifier | None:
    mode = settings.runtime_lab_intent_arbitrator_mode.strip().lower()
    if mode != "llm":
        return None
    base_url = (settings.runtime_lab_intent_arbitrator_base_url or "").strip()
    model = settings.runtime_lab_intent_arbitrator_model.strip()
    fallback_model = (settings.runtime_lab_intent_arbitrator_fallback_model or "").strip()
    api_key = (settings.runtime_lab_intent_arbitrator_api_key or "").strip()
    if not base_url or not model:
        return None
    if not api_key and not base_url.startswith("mock://"):
        return None
    client = ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type="OPENAI_COMPATIBLE",
            base_url=base_url,
            auth_config={"api_key": api_key},
        ),
        timeout=90.0,
        max_attempts=3,
        retry_sleep=2.0,
    )
    builder = OpenAIChatRequestBuilder()

    def complete(classifier_payload: dict[str, Any]) -> dict[str, Any]:
        llm_payload = builder.build(
            model=model,
            messages=[
                ChatRequestMessage(
                    role="system",
                    content=(
                        "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择，"
                        "返回 JSON 对象：selected_action, selected_candidate_id, confidence, rationale, "
                        "needs_clarification, clarification_question。不要创造候选。"
                    ),
                ),
                ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
            ],
            temperature=0.0,
            max_tokens=360,
            extra_params={
                "response_format": {"type": "json_object"},
                "reasoning": {"effort": "none", "exclude": True},
            },
        )
        started_at = perf_counter()
        actual_model = model
        try:
            response = client.complete(llm_payload)
        except Exception:
            if not fallback_model or fallback_model == model:
                raise
            fallback_payload = dict(llm_payload)
            fallback_payload["model"] = fallback_model
            actual_model = fallback_model
            response = client.complete(fallback_payload)
        parsed = _parse_llm_classifier_response(response)
        parsed_output = dict(parsed)
        parsed["_debug"] = {
            "model": actual_model,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
            "input": _redact_llm_payload(llm_payload),
            "output": parsed_output,
            "usage": _usage_from_response(response, llm_payload, parsed_output),
        }
        return parsed

    return LlmConstrainedIntentClassifier(complete)


def _parse_llm_classifier_response(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("LLM classifier response has no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise RuntimeError("LLM classifier response has no text content")
    try:
        parsed = json.loads(content)
    except JSONDecodeError:
        parsed = json.loads(_extract_json_object(content))
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM classifier response JSON is not an object")
    return parsed


def _usage_from_response(response: Mapping[str, Any], request_payload: Any, output_payload: Any) -> dict[str, Any]:
    raw_usage = response.get("usage") if isinstance(response.get("usage"), Mapping) else {}
    input_tokens = _int_value(
        raw_usage.get("prompt_tokens")
        or raw_usage.get("input_tokens")
        or raw_usage.get("promptTokens")
        or raw_usage.get("inputTokens")
    )
    output_tokens = _int_value(
        raw_usage.get("completion_tokens")
        or raw_usage.get("output_tokens")
        or raw_usage.get("completionTokens")
        or raw_usage.get("outputTokens")
    )
    total_tokens = _int_value(raw_usage.get("total_tokens") or raw_usage.get("totalTokens"))
    estimated = False
    if input_tokens == 0:
        input_tokens = _estimate_tokens(request_payload)
        estimated = True
    if output_tokens == 0:
        output_tokens = _estimate_tokens(output_payload)
        estimated = True
    if total_tokens == 0:
        total_tokens = input_tokens + output_tokens
        estimated = True
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": total_tokens,
        "estimated": estimated,
    }


def _estimate_tokens(value: Any) -> int:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, default=str)
    stripped = text.strip()
    if not stripped:
        return 0
    return max(1, int(len(stripped) / 4))


def _redact_llm_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    sanitized = dict(payload)
    if "api_key" in sanitized:
        sanitized["api_key"] = "***"
    return sanitized


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise JSONDecodeError("No JSON object found", text, 0)
    return text[start : end + 1]
