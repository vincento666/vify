from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.db_write import insert_and_fetch, insert_and_get_id
from app.core.schema import register_baseline_tables

register_baseline_tables()


def _node_selection_state_payload(
    node_key: str,
    status: str,
    existing: dict[str, Any] | None = None,
) -> dict[str, Any]:
    state = {
        "SUCCEEDED": "completed",
        "COMPLETED": "completed",
        "WAITING": "waiting",
        "RUNNING": "running",
        "FAILED": "failed",
        "CANCELLED": "cancelled",
        "SKIPPED": "skipped",
    }.get(status.upper(), "pending")
    payload = dict(existing or {})
    payload["nodeKey"] = str(payload.get("nodeKey") or payload.get("node_key") or node_key)
    payload["state"] = state
    selected = payload.get("selectedUpstreamNodeKeys") or payload.get("selected_upstream_node_keys") or []
    skipped = payload.get("skippedUpstreamNodeKeys") or payload.get("skipped_upstream_node_keys") or []
    payload["selectedUpstreamNodeKeys"] = list(selected) if isinstance(selected, list) else []
    payload["skippedUpstreamNodeKeys"] = list(skipped) if isinstance(skipped, list) else []
    payload["reason"] = str(payload.get("reason") or "")
    payload.pop("node_key", None)
    payload.pop("selected_upstream_node_keys", None)
    payload.pop("skipped_upstream_node_keys", None)
    return payload


def _runtime_ops_run_item(row: dict[str, Any]) -> dict[str, Any]:
    owner_type = str(row.get("job_owner_type") or row.get("workflow_flow_type") or "WORKFLOW").upper()
    owner_id = int(row.get("job_owner_id") or row.get("workflow_id") or 0)
    payload = row.get("job_payload") if isinstance(row.get("job_payload"), dict) else {}
    run_id = int(row["run_id"])
    queue_state = _runtime_ops_queue_state(row.get("job_status"))
    return {
        "runId": run_id,
        "ownerType": owner_type,
        "ownerId": owner_id,
        "ownerName": str(row.get("owner_name") or f"{owner_type} #{owner_id}"),
        "status": str(row.get("run_status") or "").upper(),
        "state": _runtime_ops_run_state(row.get("run_status"), row.get("job_status")),
        "tenantId": str(payload.get("tenantId") or "local"),
        "queueState": queue_state,
        "elapsedMs": int(row.get("elapsed_ms") or 0),
        "error": str(row.get("run_error") or ""),
        "leaseOwner": str(row.get("lease_owner") or ""),
        "lastHeartbeatAt": _runtime_ops_iso(row.get("last_heartbeat_at")),
        "nextRetryAt": _runtime_ops_iso(row.get("available_at")),
        "createdAt": _runtime_ops_iso(row.get("created_at")),
        "updatedAt": _runtime_ops_iso(row.get("updated_at")),
        "finishedAt": _runtime_ops_iso(row.get("finished_at")),
        "statusRef": f"/api/v1/runtime-runs/{run_id}",
        "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
        "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
        "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
    }


def _runtime_ops_run_state(run_status: Any, job_status: Any) -> str:
    normalized_run = str(run_status or "").strip().upper()
    normalized_job = str(job_status or "").strip().upper()
    if normalized_run == "RUNNING" and normalized_job == "QUEUED":
        return "queued"
    if normalized_run == "RUNNING":
        return "running"
    if normalized_run in {"INTERRUPTED", "WAITING"}:
        return "waiting"
    if normalized_run in {"SUCCEEDED", "COMPLETED"}:
        return "succeeded"
    if normalized_run == "FAILED":
        return "failed"
    if normalized_run == "CANCELLED":
        return "cancelled"
    return normalized_run.lower() or "queued"


def _runtime_ops_queue_state(job_status: Any) -> str:
    normalized = str(job_status or "").strip().upper()
    if normalized == "QUEUED":
        return "queued"
    if normalized == "RUNNING":
        return "running"
    if normalized in {"COMPLETED", "SUCCEEDED", "PUBLISHED"}:
        return "completed"
    if normalized == "FAILED":
        return "failed"
    if normalized == "CANCELLED":
        return "cancelled"
    if normalized == "IGNORED":
        return "ignored"
    return normalized.lower() or "none"


def _runtime_ops_iso(value: Any) -> str | None:
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return None


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._workflow = Base.metadata.tables["workflow"]
        self._workflow_node = Base.metadata.tables["workflow_node"]
        self._workflow_edge = Base.metadata.tables["workflow_edge"]
        self._workflow_run = Base.metadata.tables["workflow_run"]
        self._workflow_node_run = Base.metadata.tables["workflow_node_run"]
        self._runtime_job = Base.metadata.tables["runtime_jobs"]
        self._ensure_node_run_runtime_columns()

    @property
    def session(self) -> Session:
        return self._session

    def list_page(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
        flow_type: str | None = "WORKFLOW",
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._workflow.c.deleted.is_(False)]
        if flow_type:
            conditions.append(self._workflow.c.flow_type == flow_type)
        if status:
            conditions.append(self._workflow.c.status == status)
        total = self._session.execute(
            sa.select(sa.func.count()).select_from(self._workflow).where(*conditions)
        ).scalar_one()
        rows = self._session.execute(
            sa.select(self._workflow)
            .where(*conditions)
            .order_by(self._workflow.c.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).mappings().all()
        return [dict(row) for row in rows], int(total)

    def create(
        self,
        values: dict[str, Any],
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
    ) -> dict[str, Any]:
        now = datetime.now()
        insert_values = dict(values)
        flow_type = insert_values.pop("flow_type", "WORKFLOW")
        status = insert_values.pop("status", "DRAFT")
        row = insert_and_fetch(
            self._session,
            self._workflow,
            {
                **insert_values,
                "flow_type": flow_type,
                "status": status,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        workflow_id = int(row["id"])
        self._insert_nodes(workflow_id, nodes, now)
        self._insert_edges(workflow_id, edges, now)
        self._session.commit()
        return row

    def get(self, workflow_id: int, flow_type: str | None = None) -> dict[str, Any] | None:
        conditions: list[ColumnElement[bool]] = [
            self._workflow.c.id == workflow_id,
            self._workflow.c.deleted.is_(False),
        ]
        if flow_type:
            conditions.append(self._workflow.c.flow_type == flow_type)
        row = self._session.execute(
            sa.select(self._workflow).where(*conditions)
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_nodes(self, workflow_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._workflow_node)
            .where(
                self._workflow_node.c.workflow_id == workflow_id,
                self._workflow_node.c.deleted.is_(False),
            )
            .order_by(self._workflow_node.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_edges(self, workflow_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._workflow_edge)
            .where(
                self._workflow_edge.c.workflow_id == workflow_id,
                self._workflow_edge.c.deleted.is_(False),
            )
            .order_by(self._workflow_edge.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def update(
        self,
        workflow_id: int,
        values: dict[str, Any],
        nodes: list[dict[str, Any]] | None,
        edges: list[dict[str, Any]] | None,
        flow_type: str | None = None,
    ) -> dict[str, Any] | None:
        if self.get(workflow_id, flow_type) is None:
            return None
        now = datetime.now()
        if values:
            self._session.execute(
                self._workflow.update()
                .where(self._workflow.c.id == workflow_id, self._workflow.c.deleted.is_(False))
                .values(**values, updated_at=now)
            )
        if nodes is not None:
            self._session.execute(
                self._workflow_node.update()
                .where(
                    self._workflow_node.c.workflow_id == workflow_id,
                    self._workflow_node.c.deleted.is_(False),
                )
                .values(deleted=True, updated_at=now)
            )
            self._insert_nodes(workflow_id, nodes, now)
        if edges is not None:
            self._session.execute(
                self._workflow_edge.update()
                .where(
                    self._workflow_edge.c.workflow_id == workflow_id,
                    self._workflow_edge.c.deleted.is_(False),
                )
                .values(deleted=True, updated_at=now)
            )
            self._insert_edges(workflow_id, edges, now)
        self._session.commit()
        return self.get(workflow_id, flow_type)

    def delete(self, workflow_id: int, flow_type: str | None = None) -> bool:
        now = datetime.now()
        conditions: list[ColumnElement[bool]] = [
            self._workflow.c.id == workflow_id,
            self._workflow.c.deleted.is_(False),
        ]
        if flow_type:
            conditions.append(self._workflow.c.flow_type == flow_type)
        result = self._session.execute(
            self._workflow.update()
            .where(*conditions)
            .values(deleted=True, updated_at=now)
        )
        self._session.execute(
            self._workflow_node.update()
            .where(self._workflow_node.c.workflow_id == workflow_id, self._workflow_node.c.deleted.is_(False))
            .values(deleted=True, updated_at=now)
        )
        self._session.execute(
            self._workflow_edge.update()
            .where(self._workflow_edge.c.workflow_id == workflow_id, self._workflow_edge.c.deleted.is_(False))
            .values(deleted=True, updated_at=now)
        )
        self._session.commit()
        return isinstance(result, CursorResult) and result.rowcount > 0

    def create_run(self, workflow_id: int, input_values: dict[str, Any]) -> int:
        now = datetime.now()
        run_id = insert_and_get_id(
            self._session,
            self._workflow_run,
            {
                "workflow_id": workflow_id,
                "status": "RUNNING",
                "input": input_values,
                "output": {},
                "error": "",
                "elapsed_ms": 0,
                "finished_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return run_id

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._workflow_run).where(
                self._workflow_run.c.id == run_id,
                self._workflow_run.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def lock_running_run_for_event(self, run_id: int) -> dict[str, Any] | None:
        """Atomically fence a live event against a terminal run transition."""
        row = self._session.execute(
            sa.select(self._workflow_run)
            .where(
                self._workflow_run.c.id == run_id,
                self._workflow_run.c.deleted.is_(False),
                self._workflow_run.c.status == "RUNNING",
            )
            .with_for_update()
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_runtime_runs(
        self,
        *,
        page: int,
        page_size: int,
        owner_type: str | None = None,
        state: str | None = None,
        tenant_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [
            self._workflow_run.c.deleted.is_(False),
            self._workflow.c.deleted.is_(False),
        ]
        if created_from is not None:
            conditions.append(self._workflow_run.c.created_at >= created_from)
        if created_to is not None:
            conditions.append(self._workflow_run.c.created_at <= created_to)

        rows = self._session.execute(
            sa.select(
                self._workflow_run.c.id.label("run_id"),
                self._workflow_run.c.workflow_id.label("workflow_id"),
                self._workflow_run.c.status.label("run_status"),
                self._workflow_run.c.elapsed_ms.label("elapsed_ms"),
                self._workflow_run.c.error.label("run_error"),
                self._workflow_run.c.created_at.label("created_at"),
                self._workflow_run.c.updated_at.label("updated_at"),
                self._workflow_run.c.finished_at.label("finished_at"),
                self._workflow.c.name.label("owner_name"),
                self._workflow.c.flow_type.label("workflow_flow_type"),
                self._runtime_job.c.owner_type.label("job_owner_type"),
                self._runtime_job.c.owner_id.label("job_owner_id"),
                self._runtime_job.c.status.label("job_status"),
                self._runtime_job.c.lease_owner.label("lease_owner"),
                self._runtime_job.c.last_heartbeat_at.label("last_heartbeat_at"),
                self._runtime_job.c.available_at.label("available_at"),
                self._runtime_job.c.payload.label("job_payload"),
            )
            .select_from(
                self._workflow_run.join(
                    self._workflow,
                    self._workflow.c.id == self._workflow_run.c.workflow_id,
                ).outerjoin(
                    self._runtime_job,
                    sa.and_(
                        self._runtime_job.c.run_id == self._workflow_run.c.id,
                        self._runtime_job.c.job_type == "runtime_v2_completion",
                        self._runtime_job.c.deleted.is_(False),
                    ),
                )
            )
            .where(*conditions)
            .order_by(self._workflow_run.c.created_at.desc(), self._workflow_run.c.id.desc())
        ).mappings().all()

        normalized_owner_type = str(owner_type or "").strip().upper()
        normalized_state = str(state or "").strip().lower()
        normalized_tenant_id = str(tenant_id or "").strip()
        items: list[dict[str, Any]] = []
        for row in rows:
            item = _runtime_ops_run_item(dict(row))
            if normalized_owner_type and item["ownerType"] != normalized_owner_type:
                continue
            if normalized_state and item["state"] != normalized_state:
                continue
            if normalized_tenant_id and item["tenantId"] != normalized_tenant_id:
                continue
            items.append(item)

        safe_page = max(1, int(page or 1))
        safe_page_size = max(1, int(page_size or 20))
        start = (safe_page - 1) * safe_page_size
        return items[start : start + safe_page_size], len(items)

    def finish_run(
        self,
        run_id: int,
        status: str,
        output: dict[str, Any],
        error: str = "",
        elapsed_ms: int = 0,
    ) -> None:
        now = datetime.now()
        self._session.execute(
            self._workflow_run.update()
            .where(self._workflow_run.c.id == run_id)
            .values(
                status=status,
                output=output,
                error=error,
                elapsed_ms=elapsed_ms,
                finished_at=now,
                updated_at=now,
            )
        )
        self._session.commit()

    def create_node_run(
        self,
        workflow_run_id: int,
        node_key: str,
        node_type: str,
        inputs: dict[str, Any] | None = None,
        selection_state: dict[str, Any] | None = None,
    ) -> int:
        now = datetime.now()
        node_run_id = insert_and_get_id(
            self._session,
            self._workflow_node_run,
            {
                "workflow_run_id": workflow_run_id,
                "node_key": node_key,
                "node_type": node_type,
                "status": "RUNNING",
                "selection_state": _node_selection_state_payload(node_key, "RUNNING", selection_state),
                "inputs": inputs or {},
                "outputs": {},
                "error": "",
                "elapsed_ms": 0,
                "finished_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return node_run_id

    def finish_node_run(
        self,
        node_run_id: int,
        status: str,
        outputs: dict[str, Any],
        error: str = "",
        elapsed_ms: int = 0,
    ) -> None:
        now = datetime.now()
        row = self._session.execute(
            sa.select(self._workflow_node_run.c.node_key, self._workflow_node_run.c.selection_state).where(
                self._workflow_node_run.c.id == node_run_id
            )
        ).mappings().one_or_none()
        node_key = str((row or {}).get("node_key") or "")
        selection_state = (row or {}).get("selection_state")
        selection_payload = selection_state if isinstance(selection_state, dict) else None
        self._session.execute(
            self._workflow_node_run.update()
            .where(self._workflow_node_run.c.id == node_run_id)
            .values(
                status=status,
                selection_state=_node_selection_state_payload(node_key, status, selection_payload),
                outputs=outputs,
                error=error,
                elapsed_ms=elapsed_ms,
                finished_at=now,
                updated_at=now,
            )
        )
        self._session.commit()

    def list_node_runs(self, workflow_run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._workflow_node_run)
            .where(
                self._workflow_node_run.c.workflow_run_id == workflow_run_id,
                self._workflow_node_run.c.deleted.is_(False),
            )
            .order_by(self._workflow_node_run.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def _ensure_node_run_runtime_columns(self) -> None:
        bind = self._session.get_bind()
        if bind is None:
            return
        inspector = sa.inspect(bind)
        if "workflow_node_run" not in inspector.get_table_names():
            return
        column_names = {column["name"] for column in inspector.get_columns("workflow_node_run")}
        changed = False
        if "inputs" not in column_names:
            column_type = self._workflow_node_run.c.inputs.type.compile(dialect=bind.dialect)
            self._session.execute(
                sa.text(f"ALTER TABLE workflow_node_run ADD COLUMN inputs {column_type}")  # noqa: S608
            )
            self._session.execute(sa.text("UPDATE workflow_node_run SET inputs = '{}' WHERE inputs IS NULL"))
            changed = True
        if "selection_state" not in column_names:
            column_type = self._workflow_node_run.c.selection_state.type.compile(dialect=bind.dialect)
            self._session.execute(
                sa.text(f"ALTER TABLE workflow_node_run ADD COLUMN selection_state {column_type}")  # noqa: S608
            )
            rows = self._session.execute(
                sa.select(
                    self._workflow_node_run.c.id,
                    self._workflow_node_run.c.node_key,
                    self._workflow_node_run.c.status,
                )
            ).mappings()
            for row in rows:
                self._session.execute(
                    self._workflow_node_run.update()
                    .where(self._workflow_node_run.c.id == row["id"])
                    .values(selection_state=_node_selection_state_payload(str(row["node_key"]), str(row["status"])))
                )
            changed = True
        if changed:
            self._session.commit()

    def _insert_nodes(self, workflow_id: int, nodes: list[dict[str, Any]], now: datetime) -> None:
        if not nodes:
            return
        self._session.execute(
            self._workflow_node.insert(),
            [
                {
                    "workflow_id": workflow_id,
                    "node_key": node["node_key"],
                    "type": node["type"],
                    "name": node.get("name", ""),
                    "config": node.get("config", {}),
                    "deleted": False,
                    "created_at": now,
                    "updated_at": now,
                }
                for node in nodes
            ],
        )

    def _insert_edges(self, workflow_id: int, edges: list[dict[str, Any]], now: datetime) -> None:
        if not edges:
            return
        self._session.execute(
            self._workflow_edge.insert(),
            [
                {
                    "workflow_id": workflow_id,
                    "source_node_key": edge["source_node_key"],
                    "target_node_key": edge["target_node_key"],
                    "condition_expr": edge.get("condition"),
                    "deleted": False,
                    "created_at": now,
                    "updated_at": now,
                }
                for edge in edges
            ],
        )
