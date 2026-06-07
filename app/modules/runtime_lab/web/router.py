import json
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_session
from app.core.responses import success
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.payload import format_event, format_session, format_task
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.schemas import RuntimeLabMessageRequest
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository

router = APIRouter(prefix="/api/v1/runtime-lab", tags=["runtime-lab"])


def get_runtime_lab_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    bindings = _runtime_lab_chatflow_bindings(get_settings().runtime_lab_sop_chatflow_ids)
    if not bindings:
        return RuntimeLabService(RuntimeLabRepository(session))
    workflow_service = WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        chatflow_state_repository=ChatflowStateRepository(session),
    )
    adapter = ChatflowSopRuntimeAdapter(
        workflow_service,
        sop_chatflow_ids=bindings,
        fallback_adapter=FakeSopRuntimeAdapter(),
    )
    return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)


@router.post("/sessions")
def create_session(service: RuntimeLabService = Depends(get_runtime_lab_service)) -> dict[str, Any]:
    return success(format_session(service.create_session()))


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    result = service.handle_command(session_id, request.message, request.idempotency_key)
    return success(result.payload)


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
