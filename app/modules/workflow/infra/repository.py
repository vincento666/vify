from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.engine import CursorResult
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.schema import register_baseline_tables

register_baseline_tables()


class WorkflowRepository:
    def __init__(self, session: Session) -> None:
        self._session = session
        self._workflow = Base.metadata.tables["workflow"]
        self._workflow_node = Base.metadata.tables["workflow_node"]
        self._workflow_edge = Base.metadata.tables["workflow_edge"]
        self._workflow_run = Base.metadata.tables["workflow_run"]
        self._workflow_node_run = Base.metadata.tables["workflow_node_run"]

    def list_page(
        self,
        page: int,
        page_size: int,
        status: str | None = None,
    ) -> tuple[list[dict[str, Any]], int]:
        conditions: list[ColumnElement[bool]] = [self._workflow.c.deleted.is_(False)]
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
        result = self._session.execute(
            self._workflow.insert()
            .values(
                **values,
                status=values.get("status", "DRAFT"),
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._workflow)
        )
        row = dict(result.mappings().one())
        workflow_id = int(row["id"])
        self._insert_nodes(workflow_id, nodes, now)
        self._insert_edges(workflow_id, edges, now)
        self._session.commit()
        return row

    def get(self, workflow_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._workflow).where(
                self._workflow.c.id == workflow_id,
                self._workflow.c.deleted.is_(False),
            )
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
    ) -> dict[str, Any] | None:
        if self.get(workflow_id) is None:
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
        return self.get(workflow_id)

    def delete(self, workflow_id: int) -> bool:
        now = datetime.now()
        result = self._session.execute(
            self._workflow.update()
            .where(self._workflow.c.id == workflow_id, self._workflow.c.deleted.is_(False))
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
        result = self._session.execute(
            self._workflow_run.insert()
            .values(
                workflow_id=workflow_id,
                status="RUNNING",
                input=input_values,
                output={},
                error="",
                elapsed_ms=0,
                finished_at=None,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._workflow_run.c.id)
        )
        run_id = int(result.scalar_one())
        self._session.commit()
        return run_id

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

    def create_node_run(self, workflow_run_id: int, node_key: str, node_type: str) -> int:
        now = datetime.now()
        result = self._session.execute(
            self._workflow_node_run.insert()
            .values(
                workflow_run_id=workflow_run_id,
                node_key=node_key,
                node_type=node_type,
                status="RUNNING",
                outputs={},
                error="",
                elapsed_ms=0,
                finished_at=None,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
            .returning(self._workflow_node_run.c.id)
        )
        node_run_id = int(result.scalar_one())
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
        self._session.execute(
            self._workflow_node_run.update()
            .where(self._workflow_node_run.c.id == node_run_id)
            .values(
                status=status,
                outputs=outputs,
                error=error,
                elapsed_ms=elapsed_ms,
                finished_at=now,
                updated_at=now,
            )
        )
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
