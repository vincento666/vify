from __future__ import annotations

import json
import os
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import date, datetime, timedelta
from functools import lru_cache, partial
from pathlib import Path
from threading import Lock
from time import monotonic, sleep
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.host.context import RequestContext
from app.core.host.dependencies import get_request_context
from app.core.responses import success
from app.modules.ai_assistant.domain.access_scope import AiAssistantAccessScope, access_scope_for_workspace
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, create_qwen_live_planner
from app.modules.ai_assistant.domain.markdown_memory import (
    MarkdownMemoryStore,
    MemoryScopeResolver,
    ResolvedMemoryScope,
)
from app.modules.ai_assistant.domain.memory_extraction import (
    MemoryExtractionCoordinator,
    MemoryExtractor,
    create_model_memory_extractor,
)
from app.modules.ai_assistant.domain.permissions import ApprovalPolicy
from app.modules.ai_assistant.domain.session_runtime import RunControlConflict
from app.modules.ai_assistant.domain.streaming_runtime import heartbeat_payload, last_sequence
from app.modules.ai_assistant.domain.tools import ToolRegistry
from app.modules.ai_assistant.domain.usage_reporting import (
    rows_in_local_range,
    usage_session_detail,
    usage_totals_from_aggregate,
    usage_utc_bounds,
    validate_usage_range,
)
from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict
from app.modules.ai_assistant.infra.event_stream_reader import (
    AiAssistantRunEventStreamReader,
)
from app.modules.ai_assistant.infra.runtime_job_gateway import (
    AiAssistantRuntimeJobGateway,
    AiAssistantRuntimeQueueFull,
)
from app.modules.ai_assistant.web.schemas import (
    ApprovalDecisionRequest,
    CreateAiAssistantSessionRequest,
    ProcessAiAssistantRunWorkerRequest,
    SendAiAssistantMessageRequest,
)


router = APIRouter(prefix="/api/v1/ai-assistant", tags=["ai-assistant"])

_MEMORY_EXTRACTION_EXECUTOR = ThreadPoolExecutor(
    max_workers=2,
    thread_name_prefix="ai-assistant-memory",
)
_MEMORY_EXTRACTION_LOCK = Lock()
_MEMORY_EXTRACTION_IN_FLIGHT: dict[str, object] = {}
_MEMORY_EXTRACTION_REQUESTED: set[str] = set()
AI_ASSISTANT_READ_PERMISSION = "ai_assistant:read"
AI_ASSISTANT_OPERATE_PERMISSION = "ai_assistant:operate"


def require_ai_assistant_read(
    request_context: RequestContext = Depends(get_request_context),
    settings: Settings = Depends(get_settings),
) -> RequestContext:
    _ensure_ai_assistant_permission(
        request_context,
        settings,
        AI_ASSISTANT_READ_PERMISSION,
    )
    return request_context


def require_ai_assistant_operate(
    request_context: RequestContext = Depends(get_request_context),
    settings: Settings = Depends(get_settings),
) -> RequestContext:
    _ensure_ai_assistant_permission(
        request_context,
        settings,
        AI_ASSISTANT_OPERATE_PERMISSION,
    )
    return request_context


def _ensure_ai_assistant_permission(
    request_context: RequestContext,
    settings: Settings,
    required_permission: str,
) -> None:
    if settings.host_identity_mode == "local_headers":
        return
    granted = set(request_context.permissions)
    if (
        required_permission == AI_ASSISTANT_READ_PERMISSION
        and AI_ASSISTANT_OPERATE_PERMISSION in granted
    ):
        return
    if required_permission in granted or granted.intersection({"ai_assistant:*", "*"}):
        return
    raise HTTPException(
        status_code=403,
        detail=f"Missing permission {required_permission}",
    )


def get_ai_assistant_service(
    http_request: Request,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
    request_context: RequestContext = Depends(require_ai_assistant_read),
) -> AiAssistantHarnessService:
    workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT") or os.getcwd()
    access_scope = _access_scope_for_request(request_context, workspace_root)
    memory_store, memory_scope = _memory_runtime_for_scope(
        access_scope=access_scope,
        workspace_root=workspace_root,
    )
    session_factory = sessionmaker(
        bind=session.get_bind(),
        autoflush=False,
        autocommit=False,
        expire_on_commit=False,
    )
    extractor = getattr(http_request.app.state, "ai_assistant_memory_extractor", None)
    if extractor is None:
        extractor = create_model_memory_extractor(settings)
    completion_callback = None
    if extractor is not None:
        completion_callback = partial(
            _schedule_memory_extraction,
            session_factory=session_factory,
            access_scope=access_scope,
            store=memory_store,
            memory_scope=memory_scope,
            extractor=extractor,
        )
    child_execution_adapter_factory = getattr(
        http_request.app.state,
        "child_execution_adapter_factory",
        None,
    )
    child_execution_adapter = (
        child_execution_adapter_factory(session, request_context)
        if child_execution_adapter_factory is not None
        else None
    )
    return AiAssistantHarnessService(
        AiAssistantRepository(
            session,
            access_scope=access_scope,
        ),
        tool_registry=ToolRegistry.for_profile(
            settings.ai_assistant_tool_profile,
            child_execution_adapter=child_execution_adapter,
        ),
        approval_policy=ApprovalPolicy(environment=settings.deployment_environment),
        live_planner=create_qwen_live_planner(settings),
        memory_store=memory_store,
        memory_scope=memory_scope,
        memory_today=_workspace_today,
        memory_completion_callback=completion_callback,
        principal_snapshot=request_context.audit_metadata(),
        access_scope=access_scope,
    )


def get_ai_assistant_runtime_job_gateway(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> AiAssistantRuntimeJobGateway:
    return AiAssistantRuntimeJobGateway(
        session,
        active_job_limit=settings.ai_assistant_runtime_active_job_limit,
    )


def get_ai_assistant_event_stream_reader(
    session: Session = Depends(get_session),
    request_context: RequestContext = Depends(require_ai_assistant_read),
) -> AiAssistantRunEventStreamReader:
    workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT") or os.getcwd()
    reader = AiAssistantRunEventStreamReader(
        sessionmaker(
            bind=session.get_bind(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        ),
        access_scope=_access_scope_for_request(request_context, workspace_root),
    )
    session.close()
    return reader


def _access_scope_for_request(
    request_context: RequestContext,
    workspace_root: str,
) -> AiAssistantAccessScope:
    return access_scope_for_workspace(
        trusted_tenant_id=request_context.tenant_id,
        trusted_user_id=request_context.actor_id,
        trusted_workspace_root=workspace_root,
    )


def _memory_runtime_for_scope(
    *,
    access_scope: AiAssistantAccessScope,
    workspace_root: str,
) -> tuple[MarkdownMemoryStore, ResolvedMemoryScope]:
    configured_root = os.environ.get("HIFY_AI_ASSISTANT_MEMORY_ROOT")
    memory_root = Path(configured_root).expanduser() if configured_root else Path(workspace_root) / ".hify" / "memory"
    resolver, store = _memory_store_for_root(str(memory_root.resolve()))
    scope = resolver.resolve(
        trusted_tenant_id=access_scope.tenant_id,
        trusted_user_id=access_scope.user_id,
        trusted_workspace_id=access_scope.workspace_id,
    )
    return store, scope


@lru_cache(maxsize=32)
def _memory_store_for_root(root_path: str) -> tuple[MemoryScopeResolver, MarkdownMemoryStore]:
    resolver = MemoryScopeResolver(root_path)
    return resolver, MarkdownMemoryStore(resolver)


def _workspace_today() -> date:
    timezone_name = os.environ.get("HIFY_WORKSPACE_TIMEZONE", "").strip()
    if not timezone_name:
        return date.today()
    return datetime.now(ZoneInfo(timezone_name)).date()


def _schedule_memory_extraction(
    *,
    session_factory: sessionmaker[Session],
    access_scope: AiAssistantAccessScope,
    store: MarkdownMemoryStore,
    memory_scope: ResolvedMemoryScope,
    extractor: MemoryExtractor,
) -> None:
    scope_key = (
        f"{access_scope.tenant_id}\0{access_scope.user_id}"
        f"\0{access_scope.workspace_id}"
    )
    owner = object()
    with _MEMORY_EXTRACTION_LOCK:
        _MEMORY_EXTRACTION_REQUESTED.add(scope_key)
        if scope_key in _MEMORY_EXTRACTION_IN_FLIGHT:
            return
        _MEMORY_EXTRACTION_IN_FLIGHT[scope_key] = owner
    _MEMORY_EXTRACTION_EXECUTOR.submit(
        _run_memory_extraction,
        scope_key,
        owner,
        session_factory,
        access_scope,
        store,
        memory_scope,
        extractor,
    )


def _run_memory_extraction(
    scope_key: str,
    owner: object,
    session_factory: sessionmaker[Session],
    access_scope: AiAssistantAccessScope,
    store: MarkdownMemoryStore,
    memory_scope: ResolvedMemoryScope,
    extractor: MemoryExtractor,
) -> None:
    @contextmanager
    def repository_factory() -> Iterator[AiAssistantRepository]:
        with session_factory() as session:
            yield AiAssistantRepository(session, access_scope=access_scope)

    try:
        coordinator = MemoryExtractionCoordinator(
            repository_factory=repository_factory,
            store=store,
            scope=memory_scope,
            extractor=extractor,
            today=_workspace_today,
        )
        while True:
            with _MEMORY_EXTRACTION_LOCK:
                _MEMORY_EXTRACTION_REQUESTED.discard(scope_key)
            coordinator.drain()
            with _MEMORY_EXTRACTION_LOCK:
                if scope_key in _MEMORY_EXTRACTION_REQUESTED:
                    continue
                if _MEMORY_EXTRACTION_IN_FLIGHT.get(scope_key) is owner:
                    _MEMORY_EXTRACTION_IN_FLIGHT.pop(scope_key, None)
                return
    finally:
        with _MEMORY_EXTRACTION_LOCK:
            if _MEMORY_EXTRACTION_IN_FLIGHT.get(scope_key) is owner:
                _MEMORY_EXTRACTION_IN_FLIGHT.pop(scope_key, None)


@router.post("/sessions")
def create_session(
    request: CreateAiAssistantSessionRequest | None = None,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    _access: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    payload = request or CreateAiAssistantSessionRequest()
    created = service.create_session(title=payload.title, context=payload.context)
    return success(_session_payload(created))


@router.get("/sessions")
def list_sessions(service: AiAssistantHarnessService = Depends(get_ai_assistant_service)) -> dict[str, Any]:
    sessions = [_session_payload(row) for row in service.list_sessions()]
    return success({"list": sessions, "total": len(sessions)})


@router.get("/usage/summary")
def get_usage_summary(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    zone, today, _, _ = _usage_query_context(
        from_date,
        to_date,
        timezone_name,
        default_days=30,
    )
    def period(start: date | None, end: date | None) -> dict[str, Any]:
        if start is None or end is None:
            return usage_totals_from_aggregate(service.summarize_model_usage())
        started_from, started_before = usage_utc_bounds(
            timezone_name=zone,
            start=start,
            end=end,
        )
        return usage_totals_from_aggregate(
            service.summarize_model_usage(
                started_from=started_from,
                started_before=started_before,
            )
        )

    return success(
        {
            "today": period(today, today),
            "yesterday": period(today - timedelta(days=1), today - timedelta(days=1)),
            "rolling30Days": period(today - timedelta(days=29), today),
            "cumulative": period(None, None),
        }
    )


@router.get("/usage/daily")
def get_usage_daily(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    zone, _, start, end = _usage_query_context(
        from_date,
        to_date,
        timezone_name,
        default_days=365,
    )
    day_bounds = []
    day = start
    while day <= end:
        started_from, started_before = usage_utc_bounds(
            timezone_name=zone,
            start=day,
            end=day,
        )
        day_bounds.append((day.isoformat(), started_from, started_before))
        day += timedelta(days=1)
    items = [
        {"date": str(row["day"]), **usage_totals_from_aggregate(row)}
        for row in service.summarize_model_usage_daily(day_bounds=day_bounds)
    ]
    return success({"list": items, "total": len(items), "from": start.isoformat(), "to": end.isoformat()})


@router.get("/usage/sessions")
def get_usage_sessions(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    zone, _, start, end = _usage_query_context(from_date, to_date, timezone_name, default_days=30)
    started_from, started_before = usage_utc_bounds(timezone_name=zone, start=start, end=end)
    grouped = service.group_model_usage(
        group_by="session",
        started_from=started_from,
        started_before=started_before,
        limit=limit,
        offset=offset,
    )
    session_ids = [int(row["group_key"]) for row in grouped["list"]]
    titles = {
        int(row["id"]): (
            f"{row['title']}（已删除）" if row.get("deleted") else str(row["title"])
        )
        for row in service.list_usage_sessions(session_ids=session_ids)
    }
    items = [
        {
            "sessionId": int(row["group_key"]),
            "title": titles.get(int(row["group_key"]), ""),
            **usage_totals_from_aggregate(row),
        }
        for row in grouped["list"]
    ]
    return success(
        {"list": items, "total": grouped["total"], "limit": limit, "offset": offset}
    )


@router.get("/usage/dimensions")
def get_usage_dimensions(
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    zone, _, start, end = _usage_query_context(from_date, to_date, timezone_name, default_days=30)
    started_from, started_before = usage_utc_bounds(timezone_name=zone, start=start, end=end)
    providers = service.group_model_usage(
        group_by="provider",
        started_from=started_from,
        started_before=started_before,
    )["list"]
    models = service.group_model_usage(
        group_by="model",
        started_from=started_from,
        started_before=started_before,
    )["list"]
    token_types = service.summarize_model_usage_token_types(
        started_from=started_from,
        started_before=started_before,
    )
    return success(
        {
            "providers": [
                {"name": str(row["group_key"]), **usage_totals_from_aggregate(row)}
                for row in providers
            ],
            "models": [
                {"name": str(row["group_key"]), **usage_totals_from_aggregate(row)}
                for row in models
            ],
            "tokenTypes": token_types,
        }
    )


@router.get("/usage/sessions/{session_id}")
def get_usage_session_detail(
    session_id: int,
    from_date: date | None = Query(default=None, alias="from"),
    to_date: date | None = Query(default=None, alias="to"),
    timezone_name: str | None = Query(default=None, alias="timezone"),
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    assistant_session = service.get_usage_session(session_id)
    if assistant_session is None:
        raise HTTPException(status_code=404, detail="AI Assistant session not found")
    zone, _, start, end = _usage_query_context(from_date, to_date, timezone_name, default_days=30)
    started_from, started_before = usage_utc_bounds(timezone_name=zone, start=start, end=end)
    rows = rows_in_local_range(
        service.list_model_usage_calls(
            session_id=session_id,
            started_from=started_from,
            started_before=started_before,
            limit=limit,
            offset=offset,
        ),
        timezone_name=zone,
        start=start,
        end=end,
    )
    detail = usage_session_detail(
            rows,
            session_id=session_id,
            title=(
                f"{assistant_session['title']}（已删除）"
                if assistant_session.get("deleted")
                else str(assistant_session["title"])
            ),
        )
    detail.update(
        usage_totals_from_aggregate(
            service.summarize_model_usage(
                session_id=session_id,
                started_from=started_from,
                started_before=started_before,
            )
        )
    )
    detail.update({"limit": limit, "offset": offset})
    detail["sessionDeleted"] = bool(assistant_session.get("deleted"))
    return success(detail)


def _usage_query_context(
    from_date: date | None,
    to_date: date | None,
    timezone_name: str | None,
    *,
    default_days: int,
) -> tuple[str, date, date, date]:
    zone_name = (timezone_name or os.environ.get("HIFY_WORKSPACE_TIMEZONE") or "UTC").strip()
    try:
        zone = ZoneInfo(zone_name)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Invalid usage timezone") from exc
    today = datetime.now(zone).date()
    try:
        start, end = validate_usage_range(
            from_date,
            to_date,
            today=today,
            default_days=default_days,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return zone_name, today, start, end


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
    _access: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    if not service.clear_session_history(session_id):
        raise HTTPException(status_code=404, detail="AI 助手会话不存在")
    return success({"sessionId": session_id, "cleared": True})


@router.delete("/sessions/{session_id}")
def delete_session(
    session_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    _access: RequestContext = Depends(require_ai_assistant_operate),
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
    _access: RequestContext = Depends(require_ai_assistant_operate),
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
    request: SendAiAssistantMessageRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    settings: Settings = Depends(get_settings),
    runtime_jobs: AiAssistantRuntimeJobGateway = Depends(
        get_ai_assistant_runtime_job_gateway
    ),
    _access: RequestContext = Depends(require_ai_assistant_operate),
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
    runtime_job = None
    if result.run["status"] == "QUEUED":
        try:
            runtime_job = runtime_jobs.enqueue(
                run_id=int(result.run["id"]),
                session_id=int(result.run["session_id"]),
            )
        except AiAssistantRuntimeQueueFull as exc:
            raise HTTPException(status_code=429, detail=str(exc)) from exc
    payload = _turn_payload(result)
    payload["eventStreamRef"] = f"/api/v1/ai-assistant/runs/{result.run['id']}/events/stream?afterSequence=0"
    if runtime_job is not None:
        payload["runtimeJobRef"] = f"/api/v1/runtime-jobs/{runtime_job['id']}"
        payload["executionMode"] = "durable_worker"
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
    if service.get_run(run_id) is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
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
    reader: AiAssistantRunEventStreamReader = Depends(
        get_ai_assistant_event_stream_reader
    ),
) -> StreamingResponse:
    initial_cursor = _resolve_stream_cursor(after_sequence, last_event_id)
    try:
        initial_page = reader.read(run_id, after_sequence=initial_cursor)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc

    def iter_events() -> Any:
        cursor = initial_cursor
        page = initial_page
        emitted = 0
        heartbeats = 0
        next_heartbeat_at = monotonic() + max(heartbeat_ms, 1) / 1000
        while True:
            rows = page.events
            for row in rows:
                cursor = max(cursor, int(row["sequence"]))
                emitted += 1
                yield _sse_frame("ai_assistant_event", _event_payload(row))
                if test_limit is not None and emitted >= test_limit:
                    return
            run = page.run
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
            page = reader.read(run_id, after_sequence=cursor)

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
    runtime_jobs: AiAssistantRuntimeJobGateway = Depends(
        get_ai_assistant_runtime_job_gateway
    ),
    _access: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    job = runtime_jobs.get(run_id)
    if job is None and run["status"] == "QUEUED":
        job = runtime_jobs.enqueue(
            run_id=run_id,
            session_id=int(run["session_id"]),
        )
    return success(
        _run_payload(run)
        | {
            "checkpoint": _checkpoint_payload(run),
            "deprecation": {
                "deprecated": True,
                "replacement": "standalone-runtime-worker",
                "requestPayloadIgnored": request is not None,
                "sunsetAt": "2026-08-01",
                "removalGate": "external-consumer-inventory",
            },
        }
    )


@router.post("/runs/{run_id}/pause")
def pause_run(
    run_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    runtime_jobs: AiAssistantRuntimeJobGateway = Depends(
        get_ai_assistant_runtime_job_gateway
    ),
    request_context: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    actor_audit = _action_actor_audit(request_context, request.actor_id)
    try:
        run = service.pause_run(
            run_id,
            str(actor_audit["actorId"]),
            actor_audit=actor_audit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    runtime_jobs.cancel(run_id, reason="run_paused")
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


@router.post("/runs/{run_id}/resume")
def resume_run(
    run_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    runtime_jobs: AiAssistantRuntimeJobGateway = Depends(
        get_ai_assistant_runtime_job_gateway
    ),
    request_context: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    actor_audit = _action_actor_audit(request_context, request.actor_id)
    try:
        run = service.resume_run(
            run_id,
            str(actor_audit["actorId"]),
            actor_audit=actor_audit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if run["status"] == "QUEUED":
        try:
            runtime_jobs.resume(run_id)
        except KeyError:
            runtime_jobs.enqueue(
                run_id=run_id,
                session_id=int(run["session_id"]),
            )
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


@router.post("/runs/{run_id}/cancel")
def cancel_run(
    run_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    runtime_jobs: AiAssistantRuntimeJobGateway = Depends(
        get_ai_assistant_runtime_job_gateway
    ),
    request_context: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    actor_audit = _action_actor_audit(request_context, request.actor_id)
    try:
        run = service.cancel_run(
            run_id,
            str(actor_audit["actorId"]),
            actor_audit=actor_audit,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant run not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    runtime_jobs.cancel(run_id, reason="run_cancelled")
    return success(_run_payload(run) | {"checkpoint": _checkpoint_payload(run)})


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
    request_context: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    actor_audit = _action_actor_audit(request_context, request.actor_id)
    try:
        return success(
            service.approve(
                approval_id,
                str(actor_audit["actorId"]),
                actor_audit=actor_audit,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant approval not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/approvals/{approval_id}/deny")
def deny(
    approval_id: int,
    request: ApprovalDecisionRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
    request_context: RequestContext = Depends(require_ai_assistant_operate),
) -> dict[str, Any]:
    actor_audit = _action_actor_audit(request_context, request.actor_id)
    try:
        return success(
            service.deny(
                approval_id,
                str(actor_audit["actorId"]),
                request.reason,
                actor_audit=actor_audit,
            )
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="AI Assistant approval not found") from exc
    except RunControlConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


def _action_actor_audit(
    request_context: RequestContext,
    legacy_actor_id: str,
) -> dict[str, Any]:
    normalized_legacy_actor = legacy_actor_id.strip()
    audit = request_context.audit_metadata()
    if not normalized_legacy_actor:
        legacy_field_status = "absent"
    elif normalized_legacy_actor == request_context.actor_id:
        legacy_field_status = "ignored_match"
    else:
        legacy_field_status = "ignored_mismatch"
    return {
        **audit,
        "legacyActorIdField": legacy_field_status,
    }


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
