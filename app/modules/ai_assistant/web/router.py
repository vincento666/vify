from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor
from threading import Lock
from time import monotonic, sleep
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.responses import success
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, create_qwen_live_planner
from app.modules.ai_assistant.domain.session_runtime import RunControlConflict
from app.modules.ai_assistant.domain.streaming_runtime import heartbeat_payload, last_sequence
from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict
from app.modules.ai_assistant.web.schemas import (
    ApprovalDecisionRequest,
    CreateAiAssistantSessionRequest,
    ProcessAiAssistantRunWorkerRequest,
    SendAiAssistantMessageRequest,
)


router = APIRouter(prefix="/api/v1/ai-assistant", tags=["ai-assistant"])

_AUTONOMOUS_WORKER_EXECUTOR = ThreadPoolExecutor(
    max_workers=4,
    thread_name_prefix="ai-assistant-worker",
)
_AUTONOMOUS_WORKER_LOCK = Lock()
_AUTONOMOUS_WORKER_IN_FLIGHT: set[int] = set()


def get_ai_assistant_service(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AiAssistantHarnessService:
    return AiAssistantHarnessService(
        AiAssistantRepository(session),
        live_planner=create_qwen_live_planner(settings),
    )


@router.post("/sessions")
def create_session(
    request: CreateAiAssistantSessionRequest | None = None,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    payload = request or CreateAiAssistantSessionRequest()
    created = service.create_session(title=payload.title, context=payload.context)
    return success(_session_payload(created))


@router.get("/sessions")
def list_sessions(service: AiAssistantHarnessService = Depends(get_ai_assistant_service)) -> dict[str, Any]:
    sessions = [_session_payload(row) for row in service.list_sessions()]
    return success({"list": sessions, "total": len(sessions)})


@router.get("/sessions/{session_id}")
def get_ai_assistant_session(
    session_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    session = service.get_session(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    return success(_session_payload(session))


@router.delete("/sessions/{session_id}/history")
def clear_session_history(
    session_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    if not service.clear_session_history(session_id):
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    return success({"sessionId": session_id, "cleared": True})


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    if not service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    return success({"sessionId": session_id, "deleted": True})


@router.get("/sessions/{session_id}/runs")
def list_session_runs(
    session_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    if service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    runs = [_run_payload(row) for row in service.list_session_runs(session_id)]
    return success({"list": runs, "total": len(runs)})


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    request: SendAiAssistantMessageRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    try:
        result = service.run_message(
            session_id,
            request.message,
            request.idempotency_key,
            approval_mode=request.approval_mode,
            planning_strategy=request.planning_strategy,
            tool_name=request.tool_name,
            tool_input=dict(request.tool_input),
            tool_calls=[
                {"toolName": call.tool_name, "toolInput": dict(call.tool_input)}
                for call in request.tool_calls
            ],
            model_mode=request.model_mode,
            model_config=_request_model_config(request, settings),
            ai_assistant_budget=dict(request.ai_assistant_budget),
            model_budget_policy=dict(request.model_budget_policy),
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success(_turn_payload(result))


@router.post("/sessions/{session_id}/messages/async")
def start_message(
    session_id: int,
    http_request: Request,
    request: SendAiAssistantMessageRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    model_config = _request_model_config(request, settings)
    try:
        result = service.start_message(
            session_id=session_id,
            message=request.message,
            idempotency_key=request.idempotency_key,
            approval_mode=request.approval_mode,
            planning_strategy=request.planning_strategy,
            tool_name=request.tool_name,
            tool_input=dict(request.tool_input),
            tool_calls=[
                {"toolName": call.tool_name, "toolInput": dict(call.tool_input)}
                for call in request.tool_calls
            ],
            model_mode=request.model_mode,
            model_config=model_config,
            ai_assistant_budget=dict(request.ai_assistant_budget),
            model_budget_policy=dict(request.model_budget_policy),
        )
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if not result.replayed and result.run["status"] == "RUNNING":
        result = service.queue_started_message(
            session_id=session_id,
            run_id=int(result.run["id"]),
            message=request.message,
            approval_mode=request.approval_mode,
            planning_strategy=request.planning_strategy,
            tool_name=request.tool_name,
            tool_input=dict(request.tool_input),
            tool_calls=[
                {"toolName": call.tool_name, "toolInput": dict(call.tool_input)}
                for call in request.tool_calls
            ],
            model_mode=request.model_mode,
            model_config=model_config,
            ai_assistant_budget=dict(request.ai_assistant_budget),
            model_budget_policy=dict(request.model_budget_policy),
        )
        _schedule_autonomous_run_worker(
            run_id=int(result.run["id"]),
            service=service,
            model_config=model_config,
            http_request=http_request,
        )
    payload = _turn_payload(result)
    payload["eventStreamRef"] = f"/api/v1/ai-assistant/runs/{result.run['id']}/events/stream?afterSequence=0"
    return success(payload)


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    return success(_run_payload(run))


@router.get("/runs/{run_id}/inspector")
def get_run_inspector(
    run_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    inspector = service.get_run_inspector(run_id)
    if inspector is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    return success(inspector)


@router.get("/runs/{run_id}/audit")
def get_run_audit_export(
    run_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    audit = service.get_run_audit_export(run_id)
    if audit is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    return success(audit)


@router.get("/runs/{run_id}/events")
def list_run_events(
    run_id: int,
    after_sequence: int = Query(default=0, alias="afterSequence"),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    events = [_event_payload(row) for row in service.list_run_events(run_id, after_sequence=after_sequence)]
    return success({"list": events, "total": len(events)})


@router.get("/runs/{run_id}/events/stream")
def stream_run_events(
    run_id: int,
    after_sequence: int | None = Query(default=None, alias="afterSequence"),
    last_event_id: str | None = Header(default=None, alias="Last-Event-ID"),
    heartbeat_ms: int = Query(default=15000, alias="heartbeatMs"),
    test_limit: int | None = Query(default=None, alias="_testLimit"),
    test_heartbeat_limit: int | None = Query(default=None, alias="_testHeartbeatLimit"),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> StreamingResponse:
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")

    def iter_events() -> Any:
        cursor = _resolve_stream_cursor(after_sequence, last_event_id)
        emitted = 0
        heartbeats = 0
        next_heartbeat_at = monotonic() + max(heartbeat_ms, 1) / 1000
        while True:
            rows = service.list_run_events(run_id, after_sequence=cursor)
            for row in rows:
                cursor = max(cursor, int(row["sequence"]))
                emitted += 1
                yield _sse_frame("ai_assistant_event", _event_payload(row))
                if test_limit is not None and emitted >= test_limit:
                    return
            run = service.get_run(run_id)
            terminal = run is None or run["status"] in {"COMPLETED", "FAILED", "DENIED", "CANCELLED", "WAITING_APPROVAL"}
            if not rows:
                if heartbeat_ms >= 0 and (test_heartbeat_limit is not None or monotonic() >= next_heartbeat_at):
                    heartbeats += 1
                    yield _sse_frame("heartbeat", heartbeat_payload(run_id=run_id, after_sequence=cursor))
                    next_heartbeat_at = monotonic() + max(heartbeat_ms, 1) / 1000
                    if test_heartbeat_limit is not None and heartbeats >= test_heartbeat_limit:
                        return
                if terminal:
                    return
            sleep(min(max(heartbeat_ms, 1) / 1000, 0.2))

    return StreamingResponse(iter_events(), media_type="text/event-stream")


@router.get("/runs/{run_id}/snapshot")
def get_run_snapshot(
    run_id: int,
    after_sequence: int = Query(default=0, alias="afterSequence"),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    events = [_event_payload(row) for row in service.list_run_events(run_id, after_sequence=after_sequence)]
    inspector = service.get_run_inspector(run_id)
    return success(
        {
            "run": _run_payload(run),
            "events": events,
            "streamCursor": {"lastSequence": last_sequence(events, fallback=after_sequence)},
            "checkpoint": _checkpoint_payload(run),
            "inspector": inspector,
        }
    )


@router.get("/runs/{run_id}/result")
def get_run_result(
    run_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    response = dict(run.get("response_payload") or {})
    return success(
        {
            "runId": run["id"],
            "sessionId": run["session_id"],
            "status": run["status"],
            "finalAnswer": response.get("finalAnswer") or "",
            "toolCalls": response.get("toolCalls") or [],
        }
    )


@router.post("/runs/{run_id}/worker/process")
def process_run_worker(
    run_id: int,
    request: ProcessAiAssistantRunWorkerRequest | None = None,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    try:
        result = service.process_queued_run(run_id, model_config=_worker_model_config(request, settings))
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    run = result.run if result is not None else service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


@router.post("/runs/{run_id}/pause")
def pause_run(
    run_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    try:
        run = service.pause_run(run_id, request.actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


@router.post("/runs/{run_id}/resume")
def resume_run(
    run_id: int,
    http_request: Request,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    try:
        run = service.resume_run(run_id, request.actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run["status"] == "QUEUED":
        _schedule_autonomous_run_worker(
            run_id=run_id,
            service=service,
            model_config=None,
            http_request=http_request,
        )
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    try:
        run = service.cancel_run(run_id, request.actor_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


def _schedule_autonomous_run_worker(
    *,
    run_id: int,
    service: AiAssistantHarnessService,
    model_config: LivePlannerConfig | None,
    http_request: Request,
) -> bool:
    if not bool(getattr(http_request.app.state, "ai_assistant_autonomous_worker_enabled", True)):
        return False
    run_key = int(run_id)
    with _AUTONOMOUS_WORKER_LOCK:
        if run_key in _AUTONOMOUS_WORKER_IN_FLIGHT:
            return False
        _AUTONOMOUS_WORKER_IN_FLIGHT.add(run_key)

    try:
        session_factory = _worker_session_factory_from_service(service)
        worker_service_kwargs = _worker_service_kwargs(service)
        delay_seconds = float(getattr(http_request.app.state, "ai_assistant_autonomous_worker_delay_seconds", 0.05))
        _AUTONOMOUS_WORKER_EXECUTOR.submit(
            _run_autonomous_worker,
            run_key,
            session_factory,
            worker_service_kwargs,
            model_config,
            delay_seconds,
        )
    except Exception:
        with _AUTONOMOUS_WORKER_LOCK:
            _AUTONOMOUS_WORKER_IN_FLIGHT.discard(run_key)
        raise
    return True


def _run_autonomous_worker(
    run_id: int,
    session_factory: sessionmaker[Session],
    service_kwargs: dict[str, Any],
    model_config: LivePlannerConfig | None,
    delay_seconds: float,
) -> None:
    try:
        if delay_seconds > 0:
            sleep(delay_seconds)
        with session_factory() as session:
            service = AiAssistantHarnessService(AiAssistantRepository(session), **service_kwargs)
            service.process_queued_run(run_id, model_config=model_config)
    finally:
        with _AUTONOMOUS_WORKER_LOCK:
            _AUTONOMOUS_WORKER_IN_FLIGHT.discard(run_id)


def _worker_session_factory_from_service(
    service: AiAssistantHarnessService,
) -> sessionmaker[Session]:
    repository = getattr(service, "_repository")
    session = getattr(repository, "_session")
    bind = session.get_bind()
    return sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)


def _worker_service_kwargs(service: AiAssistantHarnessService) -> dict[str, Any]:
    return {
        "tool_registry": getattr(service, "_tools", None),
        "approval_policy": getattr(service, "_approval_policy", None),
        "sandbox_policy": getattr(service, "_sandbox_policy", None),
        "live_planner": getattr(service, "_live_planner", None),
        "skill_runtime": getattr(service, "_skill_runtime", None),
    }


@router.get("/tools")
def list_tools(service: AiAssistantHarnessService = Depends(get_ai_assistant_service)) -> dict[str, Any]:
    tools = service.list_tool_manifests()
    return success({"list": tools, "total": len(tools)})


@router.get("/approvals")
def list_approvals(service: AiAssistantHarnessService = Depends(get_ai_assistant_service)) -> dict[str, Any]:
    approvals = service.list_pending_approvals()
    return success({"list": approvals, "total": len(approvals)})


@router.post("/approvals/{approval_id}/approve")
def approve(
    approval_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    try:
        return success(service.approve(approval_id, request.actor_id))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant approval not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/deny")
def deny(
    approval_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    try:
        return success(service.deny(approval_id, request.actor_id, request.reason))
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant approval not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _session_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "title": row["title"],
        "status": row["status"],
        "context": row.get("context_json") or {},
        "createdAt": row["created_at"].isoformat(),
        "updatedAt": row["updated_at"].isoformat(),
    }


def _turn_payload(result: Any) -> dict[str, Any]:
    plan = _plan_payload(result.run)
    return {
        "runId": result.run["id"],
        "sessionId": result.run["session_id"],
        "status": result.run["status"],
        "replayed": result.replayed,
        "planningStrategy": plan.get("planningStrategy") or "auto_lightweight",
        "plan": plan,
        "finalAnswer": result.final_answer,
        "toolCalls": result.tool_calls,
        "approvalRequired": result.approval_required,
        "approvalId": result.approval_id,
        "sandboxDenied": result.sandbox_denied,
    }


def _run_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "status": row["status"],
        "input": row.get("input_payload") or {},
        "result": row.get("response_payload") or {},
        "startedAt": row["started_at"].isoformat() if row.get("started_at") else None,
        "completedAt": row["completed_at"].isoformat() if row.get("completed_at") else None,
    }


def _plan_payload(row: dict[str, Any]) -> dict[str, Any]:
    response_payload = dict(row.get("response_payload") or {})
    input_payload = dict(row.get("input_payload") or {})
    plan = response_payload.get("plan") or input_payload.get("plan") or {}
    return dict(plan) if isinstance(plan, dict) else {}


def _checkpoint_payload(row: dict[str, Any]) -> dict[str, Any]:
    input_payload = dict(row.get("input_payload") or {})
    runtime = input_payload.get("sessionRuntime")
    if not isinstance(runtime, dict):
        return {}
    checkpoint = runtime.get("checkpoint")
    return dict(checkpoint) if isinstance(checkpoint, dict) else {}


def _event_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "sessionId": row["session_id"],
        "runId": row["run_id"],
        "taskId": row.get("task_id"),
        "toolCallId": row.get("tool_call_id"),
        "sequence": row["sequence"],
        "type": row["type"],
        "level": row["level"],
        "status": row["status"],
        "visibleTitle": row["visible_title"],
        "visibleSummary": row["visible_summary"],
        "payload": row.get("payload") or {},
        "correlationIds": row.get("correlation_ids") or {},
        "createdAt": row["created_at"].isoformat(),
    }


def _request_model_config(
    request: SendAiAssistantMessageRequest,
    settings: Settings,
) -> LivePlannerConfig | None:
    if request.model_config_request is None:
        return None
    model_config = request.model_config_request
    return LivePlannerConfig(
        provider=model_config.provider or "openrouter",
        base_url=model_config.base_url or settings.ai_assistant_openrouter_base_url,
        model=model_config.model or settings.ai_assistant_openrouter_model,
        api_key=model_config.api_key,
        api_key_ref=model_config.api_key_ref or f"env:{settings.ai_assistant_openrouter_api_key_env}",
        temperature=model_config.temperature,
        max_tokens=model_config.max_tokens,
    )


def _worker_model_config(
    request: ProcessAiAssistantRunWorkerRequest | None,
    settings: Settings,
) -> LivePlannerConfig | None:
    if request is None or request.model_config_request is None:
        return None
    model_config = request.model_config_request
    return LivePlannerConfig(
        provider=model_config.provider or "openrouter",
        base_url=model_config.base_url or settings.ai_assistant_openrouter_base_url,
        model=model_config.model or settings.ai_assistant_openrouter_model,
        api_key=model_config.api_key,
        api_key_ref=model_config.api_key_ref or f"env:{settings.ai_assistant_openrouter_api_key_env}",
        temperature=model_config.temperature,
        max_tokens=model_config.max_tokens,
    )


def _sse_frame(event_name: str, payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    event_id = payload.get("sequence") or payload.get("afterSequence")
    id_line = f"id: {event_id}\n" if event_id is not None else ""
    return f"{id_line}event: {event_name}\ndata: {encoded}\n\n"


def _resolve_stream_cursor(after_sequence: int | None, last_event_id: str | None) -> int:
    if after_sequence is not None:
        return max(0, after_sequence)
    if not last_event_id:
        return 0
    try:
        return max(0, int(last_event_id))
    except ValueError:
        return 0
