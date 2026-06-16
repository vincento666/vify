from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables, runtime_lab_tables

ACTIVE_TASK_STATUSES = {"RUNNING", "WAITING"}


class ActiveTaskConflict(RuntimeError):
    """Raised when a session would have more than one active task."""


class RuntimeLabRepository:
    def __init__(self, session: Session) -> None:
        register_runtime_lab_tables()
        self._session = session
        self._session_table = Base.metadata.tables["runtime_lab_session"]
        self._task_table = Base.metadata.tables["runtime_lab_task"]
        self._checkpoint_table = Base.metadata.tables["runtime_lab_checkpoint"]
        self._event_table = Base.metadata.tables["runtime_lab_event"]
        self._command_table = Base.metadata.tables["runtime_lab_command"]
        self._ensure_tables()

    @property
    def session(self) -> Session:
        return self._session

    def create_session(self, status: str = "ACTIVE") -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._session_table,
            {
                "status": status,
                "active_task_id": None,
                "version": 1,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._session_table).where(
                self._session_table.c.id == session_id,
                self._session_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def append_event(self, session_id: int, event_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        now = datetime.now()
        sequence = self._next_event_sequence(session_id)
        row = insert_and_fetch(
            self._session,
            self._event_table,
            {
                "session_id": session_id,
                "sequence": sequence,
                "event_type": event_type,
                "payload": payload or {},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def create_task(
        self,
        session_id: int,
        sop_id: str,
        status: str = "RUNNING",
        current_step: str = "collect_order_no",
        parent_task_id: int | None = None,
        resume_summary: str = "",
        business_refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if status in ACTIVE_TASK_STATUSES:
            self._ensure_no_other_active_task(session_id)
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._task_table,
            {
                "session_id": session_id,
                "sop_id": sop_id,
                "status": status,
                "current_step": current_step,
                "checkpoint_id": None,
                "parent_task_id": parent_task_id,
                "resume_summary": resume_summary,
                "business_refs": business_refs or {},
                "suspended_at": None,
                "completed_at": None,
                "expires_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        if status in ACTIVE_TASK_STATUSES:
            self._set_active_task(session_id, int(row["id"]), now)
        self._session.commit()
        return row

    def get_task(self, task_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._task_table).where(
                self._task_table.c.id == task_id,
                self._task_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_active_task(self, session_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._task_table).where(
                self._task_table.c.session_id == session_id,
                self._task_table.c.status.in_(tuple(ACTIVE_TASK_STATUSES)),
                self._task_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_task_state(
        self,
        task_id: int,
        status: str,
        current_step: str | None = None,
        checkpoint_id: int | None = None,
        resume_summary: str | None = None,
        business_refs: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Runtime task not found: {task_id}")
        session_id = int(task["session_id"])
        if status in ACTIVE_TASK_STATUSES:
            self._ensure_no_other_active_task(session_id, exclude_task_id=task_id)
        now = datetime.now()
        values: dict[str, Any] = {"status": status, "updated_at": now}
        if current_step is not None:
            values["current_step"] = current_step
        if checkpoint_id is not None:
            values["checkpoint_id"] = checkpoint_id
        if resume_summary is not None:
            values["resume_summary"] = resume_summary
        if business_refs is not None:
            values["business_refs"] = business_refs
        if status == "SUSPENDED":
            values["suspended_at"] = now
        if status == "COMPLETED":
            values["completed_at"] = now
        self._session.execute(
            self._task_table.update()
            .where(self._task_table.c.id == task_id, self._task_table.c.deleted.is_(False))
            .values(**values)
        )
        if status in ACTIVE_TASK_STATUSES:
            self._set_active_task(session_id, task_id, now)
        elif int(task.get("id", 0)) == int(self.get_session(session_id)["active_task_id"] or 0):  # type: ignore[index]
            self._set_active_task(session_id, None, now)
        self._session.commit()
        updated = self.get_task(task_id)
        if updated is None:
            raise KeyError(f"Runtime task not found after update: {task_id}")
        return updated

    def create_checkpoint(
        self,
        session_id: int,
        task_id: int,
        sop_id: str,
        current_step: str,
        pending_prompt: str,
        collected: dict[str, Any] | None = None,
        scoped_variables: dict[str, Any] | None = None,
        status: str = "ACTIVE",
    ) -> dict[str, Any]:
        if status == "ACTIVE":
            self._session.execute(
                self._checkpoint_table.update()
                .where(
                    self._checkpoint_table.c.task_id == task_id,
                    self._checkpoint_table.c.status == "ACTIVE",
                    self._checkpoint_table.c.deleted.is_(False),
                )
                .values(status="SUPERSEDED", updated_at=datetime.now())
            )
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._checkpoint_table,
            {
                "session_id": session_id,
                "task_id": task_id,
                "sop_id": sop_id,
                "current_step": current_step,
                "pending_prompt": pending_prompt,
                "collected": collected or {},
                "scoped_variables": scoped_variables or {},
                "status": status,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def get_checkpoint(self, checkpoint_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._checkpoint_table).where(
                self._checkpoint_table.c.id == checkpoint_id,
                self._checkpoint_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_latest_checkpoint(self, task_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._checkpoint_table)
            .where(
                self._checkpoint_table.c.task_id == task_id,
                self._checkpoint_table.c.deleted.is_(False),
            )
            .order_by(self._checkpoint_table.c.id.desc())
            .limit(1)
        ).mappings().one_or_none()
        return dict(row) if row else None

    def list_tasks(self, session_id: int, statuses: set[str] | None = None) -> list[dict[str, Any]]:
        conditions: list[ColumnElement[bool]] = [
            self._task_table.c.session_id == session_id,
            self._task_table.c.deleted.is_(False),
        ]
        if statuses:
            conditions.append(self._task_table.c.status.in_(tuple(statuses)))
        rows = self._session.execute(
            sa.select(self._task_table).where(*conditions).order_by(self._task_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_events(self, session_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.session_id == session_id,
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def store_command_response(
        self,
        session_id: int,
        idempotency_key: str,
        request_hash: str,
        response_payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        existing = self._session.execute(
            sa.select(self._command_table).where(
                self._command_table.c.session_id == session_id,
                self._command_table.c.idempotency_key == idempotency_key,
            )
        ).mappings().one_or_none()
        if existing:
            return dict(existing), True
        row = insert_and_fetch(
            self._session,
            self._command_table,
            {
                "session_id": session_id,
                "idempotency_key": idempotency_key,
                "request_hash": request_hash,
                "response_payload": response_payload,
                "created_at": datetime.now(),
            },
        )
        self._session.commit()
        return row, False

    def get_command_response(self, session_id: int, idempotency_key: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._command_table).where(
                self._command_table.c.session_id == session_id,
                self._command_table.c.idempotency_key == idempotency_key,
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def _ensure_tables(self) -> None:
        bind = self._session.get_bind()
        if bind is None:
            return
        Base.metadata.create_all(bind=bind, tables=runtime_lab_tables())
        self._ensure_checkpoint_scoped_variables_column()

    def _ensure_checkpoint_scoped_variables_column(self) -> None:
        bind = self._session.get_bind()
        if bind is None:
            return
        inspector = sa.inspect(bind)
        if "runtime_lab_checkpoint" not in inspector.get_table_names():
            return
        column_names = {column["name"] for column in inspector.get_columns("runtime_lab_checkpoint")}
        if "scoped_variables" in column_names:
            return
        column_type = self._checkpoint_table.c.scoped_variables.type.compile(dialect=bind.dialect)
        self._session.execute(
            sa.text(f"ALTER TABLE runtime_lab_checkpoint ADD COLUMN scoped_variables {column_type}")  # noqa: S608
        )
        self._session.commit()

    def _next_event_sequence(self, session_id: int) -> int:
        value = self._session.execute(
            sa.select(sa.func.max(self._event_table.c.sequence)).where(
                self._event_table.c.session_id == session_id,
                self._event_table.c.deleted.is_(False),
            )
        ).scalar_one_or_none()
        return int(value or 0) + 1

    def _ensure_no_other_active_task(self, session_id: int, exclude_task_id: int | None = None) -> None:
        conditions: list[ColumnElement[bool]] = [
            self._task_table.c.session_id == session_id,
            self._task_table.c.status.in_(tuple(ACTIVE_TASK_STATUSES)),
            self._task_table.c.deleted.is_(False),
        ]
        if exclude_task_id is not None:
            conditions.append(self._task_table.c.id != exclude_task_id)
        existing = self._session.execute(
            sa.select(self._task_table.c.id).where(*conditions).limit(1)
        ).scalar_one_or_none()
        if existing is not None:
            raise ActiveTaskConflict("Runtime session already has an active task")

    def _set_active_task(self, session_id: int, task_id: int | None, now: datetime) -> None:
        self._session.execute(
            self._session_table.update()
            .where(self._session_table.c.id == session_id, self._session_table.c.deleted.is_(False))
            .values(active_task_id=task_id, version=self._session_table.c.version + 1, updated_at=now)
        )
