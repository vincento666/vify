import asyncio
import json
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.responses import success
from app.modules.agent.infra.repository import AgentRepository
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.llm_primary import (
    CustomerAssistantLlmRuntimeMode,
    CustomerAssistantLlmRuntimeSettings,
)
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.shadow import (
    CustomerAssistantShadowClient,
    CustomerAssistantShadowSettings,
    FakeCustomerAssistantShadowClient,
    ProviderBackedCustomerAssistantShadowClient,
)
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker, StubQaWorker
from app.modules.customer_assistant.domain.react_worker import default_restricted_react_worker
from app.modules.customer_assistant.domain.worker_registry import default_react_worker_registry
from app.modules.customer_assistant.domain.worker import TaskWorker
from app.modules.customer_assistant.domain.worker_runtime import CustomerAssistantWorkerRuntime
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.web.schemas import (
    CustomerAssistantSessionCreateRequest,
    CustomerAssistantSpawnSubAgentRequest,
    CustomerAssistantTurnRequest,
)
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


router = APIRouter(prefix="/api/v1/customer-assistant", tags=["customer-assistant"])
CUSTOMER_ASSISTANT_LLM_AGENT_NAME = "034 RuntimeLab Airline Chatflow LLM Agent"


def get_customer_assistant_service(
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> CustomerAssistantService:
    return build_customer_assistant_service(session, settings)


def build_customer_assistant_service(session: Session, settings: Settings) -> CustomerAssistantService:
    shadow_settings = CustomerAssistantShadowSettings.from_settings(settings)
    llm_runtime_settings = CustomerAssistantLlmRuntimeSettings.from_settings(settings)
    workers = _customer_assistant_workers(session, settings)
    return CustomerAssistantService(
        CustomerAssistantRepository(session),
        scheduler=LocalWorkerScheduler(workers),
        shadow_settings=shadow_settings,
        shadow_client=_customer_assistant_shadow_client(session, shadow_settings),
        llm_runtime_settings=llm_runtime_settings,
        llm_primary_client=_customer_assistant_primary_client(session, llm_runtime_settings),
        async_worker_runtime=CustomerAssistantWorkerRuntime(
            workers=workers,
            session_factory=_customer_assistant_worker_session_factory(session),
            async_worker_types={"stub_qa", "chatflow_sop"},
            wait_deadline_seconds=settings.customer_assistant_worker_wait_deadline_seconds,
            task_timeout_seconds=settings.customer_assistant_worker_timeout_seconds,
        ),
    )


def _customer_assistant_scheduler(session: Session, settings: Settings) -> LocalWorkerScheduler:
    return LocalWorkerScheduler(_customer_assistant_workers(session, settings))


def _customer_assistant_workers(session: Session, settings: Settings) -> dict[str, TaskWorker]:
    bindings = _customer_assistant_chatflow_bindings(settings.runtime_lab_sop_chatflow_ids)
    adapter = _customer_assistant_sop_adapter(session, bindings)
    react_registry = default_react_worker_registry()
    refund_status_worker = react_registry.lookup("refund_status", "refund_status_react")
    workers = {
        "chatflow_sop": ChatflowSopWorker(adapter),
        "stub_qa": StubQaWorker(delay_seconds=settings.customer_assistant_stub_qa_delay_seconds),
    }
    if refund_status_worker is not None:
        workers["react_worker"] = default_restricted_react_worker(refund_status_worker)
    return workers


def _customer_assistant_worker_session_factory(session: Session):
    bind = session.get_bind()
    return sessionmaker(bind=bind, autoflush=False, autocommit=False, expire_on_commit=False)


def _customer_assistant_shadow_client(
    session: Session,
    settings: CustomerAssistantShadowSettings,
) -> CustomerAssistantShadowClient | None:
    if settings.mode == "fake":
        return FakeCustomerAssistantShadowClient()
    if settings.mode == "live" and settings.model_config_id is not None:
        return ProviderBackedCustomerAssistantShadowClient(
            ProviderModelFacade(session),
            model_config_id=settings.model_config_id,
        )
    return None


def _customer_assistant_primary_client(
    session: Session,
    settings: CustomerAssistantLlmRuntimeSettings,
) -> CustomerAssistantShadowClient | None:
    if (
        settings.mode == CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK
        and settings.model_config_id is not None
    ):
        return ProviderBackedCustomerAssistantShadowClient(
            ProviderModelFacade(session),
            model_config_id=settings.model_config_id,
        )
    if settings.mode == CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK:
        return FakeCustomerAssistantShadowClient()
    return None


def _customer_assistant_sop_adapter(session: Session, bindings: dict[str, int]):
    fallback_adapter = FakeSopRuntimeAdapter()
    if not bindings:
        return fallback_adapter
    workflow_service = WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        agent_repository=AgentRepository(session),
        model_facade=ProviderModelFacade(session),
        chatflow_state_repository=ChatflowStateRepository(session),
        preferred_llm_agent_name=CUSTOMER_ASSISTANT_LLM_AGENT_NAME,
    )
    return ChatflowSopRuntimeAdapter(
        workflow_service,
        sop_chatflow_ids=bindings,
        fallback_adapter=fallback_adapter,
        runtime_v2_service=ChatflowRuntimeV2Service(
            WorkflowRepository(session),
            ChatflowStateRepository(session),
        ),
    )


def _customer_assistant_chatflow_bindings(raw: str | None) -> dict[str, int]:
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except JSONDecodeError:
            return _customer_assistant_chatflow_bindings(text.strip("{}"))
        if not isinstance(parsed, dict):
            return {}
        return {str(key): int(value) for key, value in parsed.items() if str(key).strip()}
    bindings: dict[str, int] = {}
    for item in text.split(","):
        sop_id, _, chatflow_id = item.partition(":")
        if sop_id.strip() and chatflow_id.strip():
            bindings[sop_id.strip()] = int(chatflow_id.strip())
    return bindings


@router.post("/sessions")
def create_session(
    request: CustomerAssistantSessionCreateRequest | None = None,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    context = request.context if request else {}
    return success(service.create_session(context))


@router.post("/sessions/{session_id}/turns")
def submit_turn(
    session_id: int,
    request: CustomerAssistantTurnRequest,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.handle_turn(session_id, request.message, request.idempotency_key, request.actor))


@router.post("/harness/spawn-sub-agent")
def spawn_sub_agent(
    request: CustomerAssistantSpawnSubAgentRequest,
    background_tasks: BackgroundTasks,
    session: Session = Depends(get_session),
    settings: Settings = Depends(get_settings),
) -> dict[str, Any]:
    service = build_customer_assistant_service(session, settings)
    arguments = request.arguments
    spawned = service.spawn_sub_agent(
        session_id=arguments.session_id,
        message=arguments.input.message,
        actor=arguments.input.actor,
        event_level=arguments.event_level,
    )
    background_session_factory = _customer_assistant_worker_session_factory(session)
    background_tasks.add_task(
        _run_spawned_sub_agent_background,
        background_session_factory,
        settings,
        int(spawned["runId"]),
        int(spawned["sessionId"]),
        arguments.input.message,
        arguments.input.actor,
        arguments.event_level,
    )
    return success(spawned)


def _run_spawned_sub_agent_background(
    session_factory,
    settings: Settings,
    run_id: int,
    session_id: int,
    message: str,
    actor: str,
    event_level: str,
) -> None:
    with session_factory() as session:
        service = build_customer_assistant_service(session, settings)
        service.run_spawned_sub_agent(run_id, session_id, message, actor, event_level)


@router.get("/runs/{run_id}")
def get_sub_agent_run(
    run_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.get_sub_agent_run(run_id))


@router.post("/worker-runs/{worker_run_id}/cancel")
def cancel_worker_run(
    worker_run_id: str,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.cancel_worker_run(worker_run_id))


@router.get("/worker-runs/{worker_run_id}")
def get_worker_run(
    worker_run_id: str,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.get_worker_run(worker_run_id))


@router.get("/worker-runs/{worker_run_id}/result")
def get_worker_result(
    worker_run_id: str,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.get_worker_result(worker_run_id))


@router.get("/worker-runs/{worker_run_id}/events")
def list_worker_events(
    worker_run_id: str,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.list_worker_events(worker_run_id))


@router.get("/worker-runs/{worker_run_id}/events/stream")
def stream_worker_events(
    worker_run_id: str,
    request: Request,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    heartbeat_ms: int = Query(default=1000, alias="heartbeatMs", ge=100, le=30000),
    test_limit: int | None = Query(default=None, alias="_testLimit", ge=1, le=1000),
    test_heartbeat_limit: int | None = Query(default=None, alias="_testHeartbeatLimit", ge=1, le=1000),
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> StreamingResponse:
    return StreamingResponse(
        _iter_customer_assistant_worker_sse(
            service,
            worker_run_id=worker_run_id,
            request=request,
            after_sequence=after_sequence,
            heartbeat_ms=heartbeat_ms,
            test_limit=test_limit,
            test_heartbeat_limit=test_heartbeat_limit,
        ),
        media_type="text/event-stream",
    )


@router.get("/sessions/{session_id}/tasks")
def list_tasks(
    session_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.list_tasks(session_id))


@router.post("/sessions/{session_id}/worker-results/refresh")
def refresh_worker_results(
    session_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.refresh_worker_results(session_id))


@router.get("/sessions/{session_id}/events")
def list_events(
    session_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.list_events(session_id))


@router.get("/sessions/{session_id}/events/stream")
def stream_events(
    session_id: int,
    request: Request,
    after_sequence: int = Query(default=0, alias="afterSequence", ge=0),
    heartbeat_ms: int = Query(default=1000, alias="heartbeatMs", ge=100, le=30000),
    test_limit: int | None = Query(default=None, alias="_testLimit", ge=1, le=1000),
    test_heartbeat_limit: int | None = Query(default=None, alias="_testHeartbeatLimit", ge=1, le=1000),
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> StreamingResponse:
    start_after = _stream_start_sequence(request, after_sequence)
    return StreamingResponse(
        _iter_customer_assistant_sse(
            service,
            session_id=session_id,
            request=request,
            after_sequence=start_after,
            heartbeat_ms=heartbeat_ms,
            test_limit=test_limit,
            test_heartbeat_limit=test_heartbeat_limit,
        ),
        media_type="text/event-stream",
    )


@router.post("/proposed-actions/{action_id}/confirm")
def confirm_action(
    action_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.confirm_action(action_id))


@router.post("/proposed-actions/{action_id}/reject")
def reject_action(
    action_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.reject_action(action_id))


@router.post("/proposed-actions/{action_id}/execute")
def execute_action(
    action_id: int,
    service: CustomerAssistantService = Depends(get_customer_assistant_service),
) -> dict[str, Any]:
    return success(service.execute_action(action_id))


async def _iter_customer_assistant_sse(
    service: CustomerAssistantService,
    *,
    session_id: int,
    request: Request,
    after_sequence: int,
    heartbeat_ms: int,
    test_limit: int | None,
    test_heartbeat_limit: int | None,
):
    last_sequence = after_sequence
    heartbeat_seconds = heartbeat_ms / 1000
    emitted = 0
    heartbeats = 0
    while True:
        rows = service.list_events_after(session_id, last_sequence)
        if rows:
            for row in rows:
                last_sequence = int(row["sequence"])
                yield _sse_frame(row)
                emitted += 1
                if test_limit is not None and emitted >= test_limit:
                    return
            await asyncio.sleep(0)
            continue
        if await request.is_disconnected():
            break
        yield ": heartbeat\n\n"
        heartbeats += 1
        if test_heartbeat_limit is not None and heartbeats >= test_heartbeat_limit:
            return
        await asyncio.sleep(heartbeat_seconds)


async def _iter_customer_assistant_worker_sse(
    service: CustomerAssistantService,
    *,
    worker_run_id: str,
    request: Request,
    after_sequence: int,
    heartbeat_ms: int,
    test_limit: int | None,
    test_heartbeat_limit: int | None,
):
    last_sequence = after_sequence
    heartbeat_seconds = heartbeat_ms / 1000
    emitted = 0
    heartbeats = 0
    while True:
        rows = service.list_worker_events_after(worker_run_id, last_sequence)
        if rows:
            for row in rows:
                last_sequence = int(row["sequence"])
                yield _worker_sse_frame(row)
                emitted += 1
                if test_limit is not None and emitted >= test_limit:
                    return
            await asyncio.sleep(0)
            continue
        if await request.is_disconnected():
            break
        yield ": heartbeat\n\n"
        heartbeats += 1
        if test_heartbeat_limit is not None and heartbeats >= test_heartbeat_limit:
            return
        await asyncio.sleep(heartbeat_seconds)


def _stream_start_sequence(request: Request, after_sequence: int) -> int:
    if after_sequence:
        return after_sequence
    raw = request.headers.get("last-event-id") or request.headers.get("Last-Event-ID")
    try:
        return max(0, int(raw or 0))
    except ValueError:
        return 0


def _sse_frame(event: dict[str, Any]) -> str:
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event['sequence']}\nevent: customer_assistant_event\ndata: {payload}\n\n"


def _worker_sse_frame(event: dict[str, Any]) -> str:
    payload = json.dumps(event, ensure_ascii=False, separators=(",", ":"))
    return f"id: {event['sequence']}\nevent: customer_assistant_worker_event\ndata: {payload}\n\n"
