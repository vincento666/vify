from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import Base, get_session
from app.core.responses import success
from app.core.sanitization import sanitize_value
from app.core.schema import register_baseline_tables
from app.modules.workflow.web.schemas import format_datetime

register_baseline_tables()

router = APIRouter(prefix="/api/v1/observe", tags=["observe"])


class ObserveService:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._workflow = Base.metadata.tables["workflow"]
        self._workflow_run = Base.metadata.tables["workflow_run"]
        self._workflow_node_run = Base.metadata.tables["workflow_node_run"]
        self._chatflow_session = Base.metadata.tables["chatflow_session"]
        self._chatflow_event = Base.metadata.tables["chatflow_event"]
        self._handoff_ticket = Base.metadata.tables["handoff_ticket"]
        self._audit_record = Base.metadata.tables["audit_record"]

    def list_runs(self, page: int, page_size: int, flow_type: str | None = None) -> dict[str, Any]:
        conditions = [self._workflow_run.c.deleted.is_(False), self._workflow.c.deleted.is_(False)]
        if flow_type:
            conditions.append(self._workflow.c.flow_type == flow_type)
        total = self._session.execute(
            sa.select(sa.func.count())
            .select_from(self._workflow_run.join(self._workflow, self._workflow_run.c.workflow_id == self._workflow.c.id))
            .where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(
                self._workflow_run,
                self._workflow.c.flow_type,
                self._workflow.c.name.label("workflow_name"),
                self._chatflow_session.c.channel,
                self._chatflow_session.c.user_id,
                self._chatflow_session.c.session_id,
            )
            .select_from(
                self._workflow_run
                .join(self._workflow, self._workflow_run.c.workflow_id == self._workflow.c.id)
                .outerjoin(self._chatflow_session, self._chatflow_session.c.current_run_id == self._workflow_run.c.id)
            )
            .where(*conditions)
            .order_by(self._workflow_run.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return {"list": [self._run_row(row) for row in rows], "total": int(total), "page": page, "pageSize": page_size}

    def get_run(self, run_id: int) -> dict[str, Any]:
        row = self._session.execute(
            sa.select(
                self._workflow_run,
                self._workflow.c.flow_type,
                self._workflow.c.name.label("workflow_name"),
                self._chatflow_session.c.channel,
                self._chatflow_session.c.user_id,
                self._chatflow_session.c.session_id,
            )
            .select_from(
                self._workflow_run
                .join(self._workflow, self._workflow_run.c.workflow_id == self._workflow.c.id)
                .outerjoin(self._chatflow_session, self._chatflow_session.c.current_run_id == self._workflow_run.c.id)
            )
            .where(self._workflow_run.c.id == run_id, self._workflow_run.c.deleted.is_(False))
        ).mappings().one()
        node_runs = self._session.execute(
            sa.select(self._workflow_node_run)
            .where(
                self._workflow_node_run.c.workflow_run_id == run_id,
                self._workflow_node_run.c.deleted.is_(False),
            )
            .order_by(self._workflow_node_run.c.id.asc())
        ).mappings().all()
        events = self._session.execute(
            sa.select(self._chatflow_event)
            .where(self._chatflow_event.c.run_id == run_id, self._chatflow_event.c.deleted.is_(False))
            .order_by(self._chatflow_event.c.sequence.asc())
        ).mappings().all()
        data = self._run_row(row)
        data["input"] = sanitize_value(row["input"] or {})
        data["output"] = sanitize_value(row["output"] or {})
        data["error"] = row["error"] or ""
        data["nodeRuns"] = [self._node_run_row(dict(item)) for item in node_runs]
        data["events"] = [self._event_row(dict(item)) for item in events]
        return data

    def list_sessions(self, page: int, page_size: int) -> dict[str, Any]:
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._chatflow_session).where(self._chatflow_session.c.deleted.is_(False))
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._chatflow_session)
            .where(self._chatflow_session.c.deleted.is_(False))
            .order_by(self._chatflow_session.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return {"list": [self._session_row(dict(row)) for row in rows], "total": int(total), "page": page, "pageSize": page_size}

    def metrics(self) -> dict[str, Any]:
        run_count = int(self._session.execute(sa.select(sa.func.count()).select_from(self._workflow_run).where(self._workflow_run.c.deleted.is_(False))).scalar_one())
        handoff_count = int(self._session.execute(sa.select(sa.func.count()).select_from(self._handoff_ticket).where(self._handoff_ticket.c.deleted.is_(False))).scalar_one())
        channel_rows = self._session.execute(
            sa.select(self._chatflow_session.c.channel, sa.func.count().label("count"))
            .where(self._chatflow_session.c.deleted.is_(False))
            .group_by(self._chatflow_session.c.channel)
        ).mappings().all()
        status_rows = self._session.execute(
            sa.select(self._workflow_run.c.status, sa.func.count().label("count"))
            .where(self._workflow_run.c.deleted.is_(False))
            .group_by(self._workflow_run.c.status)
        ).mappings().all()
        return {
            "runCount": run_count,
            "handoffCount": handoff_count,
            "handoffRate": handoff_count / run_count if run_count else 0,
            "channelDistribution": {str(row["channel"] or "unknown"): int(row["count"]) for row in channel_rows},
            "statusDistribution": {str(row["status"] or "UNKNOWN"): int(row["count"]) for row in status_rows},
            "channelDeliveryFailures": self._channel_delivery_failures(),
        }

    def _run_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "runId": int(row["id"]),
            "workflowId": int(row["workflow_id"]),
            "workflowName": row["workflow_name"],
            "flowType": row["flow_type"],
            "status": row["status"],
            "elapsedMs": int(row["elapsed_ms"] or 0),
            "channel": row["channel"] or "",
            "userId": row["user_id"] or "",
            "sessionId": row["session_id"] or "",
            "createdAt": format_datetime(row["created_at"]),
            "finishedAt": format_datetime(row["finished_at"]) if row.get("finished_at") else None,
        }

    def _node_run_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "nodeKey": row["node_key"],
            "nodeType": row["node_type"],
            "status": row["status"],
            "outputs": sanitize_value(row["outputs"] or {}),
            "error": row["error"] or "",
            "elapsedMs": int(row["elapsed_ms"] or 0),
        }

    def _event_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "type": row["event_type"],
            "sequence": int(row["sequence"]),
            "nodeKey": row["node_key"],
            "payload": sanitize_value(row["payload"] or {}),
            "createdAt": format_datetime(row["created_at"]),
        }

    def _session_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "sessionId": row["session_id"],
            "chatflowId": int(row["chatflow_id"]),
            "conversationId": row["conversation_id"],
            "userId": row["user_id"],
            "channel": row["channel"],
            "channelId": row["channel_id"],
            "status": row["status"],
            "currentRunId": int(row["current_run_id"] or 0),
            "createdAt": format_datetime(row["created_at"]),
            "updatedAt": format_datetime(row["updated_at"]),
        }

    def _channel_delivery_failures(self) -> int:
        return int(
            self._session.execute(
                sa.select(sa.func.count())
                .select_from(self._audit_record)
                .where(
                    self._audit_record.c.deleted.is_(False),
                    self._audit_record.c.action == "CHANNEL_DELIVERY_FAILED",
                    self._audit_record.c.status == "failed",
                )
            ).scalar_one()
        )


def get_observe_service(session: Session = Depends(get_session)) -> ObserveService:
    return ObserveService(session)


@router.get("/runs")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    flow_type: str | None = Query(None, alias="flowType"),
    service: ObserveService = Depends(get_observe_service),
) -> dict[str, Any]:
    return success(service.list_runs(page, page_size, flow_type))


@router.get("/runs/{run_id}")
def get_run(run_id: int, service: ObserveService = Depends(get_observe_service)) -> dict[str, Any]:
    return success(service.get_run(run_id))


@router.get("/sessions")
def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    service: ObserveService = Depends(get_observe_service),
) -> dict[str, Any]:
    return success(service.list_sessions(page, page_size))


@router.get("/metrics")
def metrics(service: ObserveService = Depends(get_observe_service)) -> dict[str, Any]:
    return success(service.metrics())
