from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.schemas import (
    RuntimeLabMessageRequest,
    format_event,
    format_session,
    format_task,
    format_turn,
)

router = APIRouter(prefix="/api/v1/runtime-lab", tags=["runtime-lab"])


def get_runtime_lab_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(RuntimeLabRepository(session))


@router.post("/sessions")
def create_session(service: RuntimeLabService = Depends(get_runtime_lab_service)) -> dict[str, Any]:
    return success(format_session(service.create_session()))


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    return success(format_turn(service.handle_message(session_id, request.message)))


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
