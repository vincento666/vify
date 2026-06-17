from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.infra.repository import AiAssistantRepository, IdempotencyConflict
from app.modules.ai_assistant.web.schemas import CreateAiAssistantSessionRequest, SendAiAssistantMessageRequest


router = APIRouter(prefix="/api/v1/ai-assistant", tags=["ai-assistant"])


def get_ai_assistant_service(session: Session = Depends(get_session)) -> AiAssistantHarnessService:
    return AiAssistantHarnessService(AiAssistantRepository(session))


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
        raise HTTPException(status_code=404, detail="AI Assistant session not found")
    return success(_session_payload(session))


@router.post("/sessions/{session_id}/messages")
def send_message(
    session_id: int,
    request: SendAiAssistantMessageRequest,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    if service.get_session(session_id) is None:
        raise HTTPException(status_code=404, detail="AI Assistant session not found")
    try:
        result = service.run_message(session_id, request.message, request.idempotency_key)
    except IdempotencyConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return success(_turn_payload(result))


@router.get("/runs/{run_id}")
def get_run(
    run_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    run = service.get_run(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="AI Assistant run not found")
    return success(_run_payload(run))


@router.get("/runs/{run_id}/events")
def list_run_events(
    run_id: int,
    service: AiAssistantHarnessService = Depends(get_ai_assistant_service),
) -> dict[str, Any]:
    events = [_event_payload(row) for row in service.list_run_events(run_id)]
    return success({"list": events, "total": len(events)})


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


@router.get("/tools")
def list_tools(service: AiAssistantHarnessService = Depends(get_ai_assistant_service)) -> dict[str, Any]:
    tools = service.list_tool_manifests()
    return success({"list": tools, "total": len(tools)})


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
    return {
        "runId": result.run["id"],
        "sessionId": result.run["session_id"],
        "status": result.run["status"],
        "replayed": result.replayed,
        "finalAnswer": result.final_answer,
        "toolCalls": result.tool_calls,
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
