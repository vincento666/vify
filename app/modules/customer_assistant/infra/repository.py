from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.modules.customer_assistant.infra.schema import customer_assistant_tables, register_customer_assistant_tables


_SEQUENCE_RETRY_ATTEMPTS = 3


class IdempotencyConflict(RuntimeError):
    pass


class CustomerAssistantRepository:
    def __init__(self, session: Session) -> None:
        register_customer_assistant_tables()
        self._session = session
        self._session_table = Base.metadata.tables["customer_assistant_session"]
        self._run_table = Base.metadata.tables["customer_assistant_run"]
        self._task_table = Base.metadata.tables["customer_assistant_task"]
        self._event_table = Base.metadata.tables["customer_assistant_event"]
        self._worker_run_table = Base.metadata.tables["customer_assistant_worker_run"]
        self._worker_event_table = Base.metadata.tables["customer_assistant_worker_event"]
        self._action_table = Base.metadata.tables["customer_assistant_proposed_action"]
        self._ensure_tables()

    @property
    def session(self) -> Session:
        return self._session

    def create_session(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._session_table,
            {
                "status": "ACTIVE",
                "context_json": context or {},
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

    def list_demo_sessions(self, demo_seed: str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._session_table)
            .where(self._session_table.c.deleted.is_(False))
            .order_by(self._session_table.c.id.asc())
        ).mappings().all()
        demo_rows: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            context = dict(item.get("context_json") or {})
            if context.get("demoSeed") == demo_seed:
                demo_rows.append(item)
        return demo_rows

    def create_run(
        self,
        session_id: int,
        idempotency_key: str | None,
        request_hash: str,
        input_payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        if idempotency_key:
            existing = self.get_run_by_idempotency(session_id, idempotency_key)
            if existing is not None:
                if existing["request_hash"] != request_hash:
                    raise IdempotencyConflict("Idempotency key reused with different request")
                return existing, True
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._run_table,
            {
                "session_id": session_id,
                "idempotency_key": idempotency_key,
                "request_hash": request_hash,
                "status": "RUNNING",
                "input_payload": input_payload,
                "response_payload": None,
                "warnings_json": [],
                "started_at": now,
                "completed_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row, False

    def get_run_by_idempotency(self, session_id: int, idempotency_key: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._run_table).where(
                self._run_table.c.session_id == session_id,
                self._run_table.c.idempotency_key == idempotency_key,
                self._run_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._run_table).where(
                self._run_table.c.id == run_id,
                self._run_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def complete_run(
        self,
        run_id: int,
        response_payload: dict[str, Any],
        status: str = "COMPLETED",
        warnings: list[str] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._run_table.update()
            .where(self._run_table.c.id == run_id, self._run_table.c.deleted.is_(False))
            .values(
                status=status,
                response_payload=response_payload,
                warnings_json=warnings or [],
                completed_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        updated = self._session.execute(
            sa.select(self._run_table).where(self._run_table.c.id == run_id)
        ).mappings().one()
        return dict(updated)

    def upsert_task(
        self,
        session_id: int,
        task_key: str,
        task_type: str,
        business_key: str,
        worker_type: str,
        worker_ref: str,
        input_snapshot: dict[str, Any] | None = None,
        status: str = "PENDING",
    ) -> dict[str, Any]:
        existing = self.get_task_by_key(session_id, task_key)
        now = datetime.now()
        if existing is not None:
            self._session.execute(
                self._task_table.update()
                .where(self._task_table.c.id == existing["id"], self._task_table.c.deleted.is_(False))
                .values(
                    input_snapshot_json=input_snapshot or existing.get("input_snapshot_json") or {},
                    version=self._task_table.c.version + 1,
                    updated_at=now,
                )
            )
            self._session.commit()
            updated = self.get_task(int(existing["id"]))
            if updated is None:
                raise KeyError(f"Customer assistant task disappeared: {existing['id']}")
            return updated
        row = insert_and_fetch(
            self._session,
            self._task_table,
            {
                "session_id": session_id,
                "task_key": task_key,
                "task_type": task_type,
                "business_key": business_key,
                "short_id": self._short_id(task_key),
                "status": status,
                "worker_type": worker_type,
                "worker_ref": worker_ref,
                "checkpoint_json": {},
                "input_snapshot_json": input_snapshot or {},
                "last_result_json": {},
                "proposed_actions_json": [],
                "version": 1,
                "completed_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
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

    def get_task_by_key(self, session_id: int, task_key: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._task_table).where(
                self._task_table.c.session_id == session_id,
                self._task_table.c.task_key == task_key,
                self._task_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_task(
        self,
        task_id: int,
        *,
        status: str | None = None,
        checkpoint: dict[str, Any] | None = None,
        last_result: dict[str, Any] | None = None,
        proposed_actions: list[dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        task = self.get_task(task_id)
        if task is None:
            raise KeyError(f"Customer assistant task not found: {task_id}")
        now = datetime.now()
        values: dict[str, Any] = {"updated_at": now, "version": self._task_table.c.version + 1}
        if status is not None:
            values["status"] = status
            if status in {"COMPLETED", "FAILED", "CANCELLED"}:
                values["completed_at"] = now
        if checkpoint is not None:
            values["checkpoint_json"] = checkpoint
        if last_result is not None:
            values["last_result_json"] = last_result
        if proposed_actions is not None:
            values["proposed_actions_json"] = proposed_actions
        self._session.execute(
            self._task_table.update()
            .where(self._task_table.c.id == task_id, self._task_table.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        updated = self.get_task(task_id)
        if updated is None:
            raise KeyError(f"Customer assistant task not found after update: {task_id}")
        return updated

    def list_tasks(self, session_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._task_table)
            .where(
                self._task_table.c.session_id == session_id,
                self._task_table.c.deleted.is_(False),
            )
            .order_by(self._task_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def append_event(
        self,
        session_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        run_id: int | None = None,
        task_id: int | None = None,
        visibility: str = "operator",
        source: str = "customer_assistant",
        actor: str = "customer",
        parent_span_id: str | None = None,
        span_id: str | None = None,
    ) -> dict[str, Any]:
        for attempt in range(_SEQUENCE_RETRY_ATTEMPTS):
            now = datetime.now()
            sequence = self._next_event_sequence(session_id)
            try:
                row = insert_and_fetch(
                    self._session,
                    self._event_table,
                    {
                        "session_id": session_id,
                        "run_id": run_id,
                        "sequence": sequence,
                        "type": event_type,
                        "visibility": visibility,
                        "source": source,
                        "actor": actor,
                        "task_id": task_id,
                        "parent_span_id": parent_span_id,
                        "span_id": span_id,
                        "payload": payload or {},
                        "deleted": False,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                self._session.commit()
                return row
            except sa.exc.IntegrityError as exc:
                self._session.rollback()
                if attempt == _SEQUENCE_RETRY_ATTEMPTS - 1 or not _is_sequence_conflict(exc):
                    raise
        raise RuntimeError("Could not append customer assistant event after sequence retries")

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

    def list_events_after(self, session_id: int, after_sequence: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.session_id == session_id,
                self._event_table.c.sequence > after_sequence,
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def create_worker_run(
        self,
        *,
        session_id: int,
        parent_run_id: int,
        task_id: int,
        worker_type: str,
        worker_ref: str,
        idempotency_key: str,
        request_hash: str,
        input_payload: dict[str, Any],
    ) -> tuple[dict[str, Any], bool]:
        existing = self.get_worker_run_by_idempotency(idempotency_key)
        if existing is not None:
            if existing["request_hash"] != request_hash:
                raise IdempotencyConflict("Worker idempotency key reused with different request")
            return existing, True
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._worker_run_table,
            {
                "session_id": session_id,
                "parent_run_id": parent_run_id,
                "task_id": task_id,
                "worker_type": worker_type,
                "worker_ref": worker_ref,
                "idempotency_key": idempotency_key,
                "request_hash": request_hash,
                "status": "QUEUED",
                "input_payload": _redact_payload(input_payload),
                "result_payload": None,
                "error_json": None,
                "queued_at": now,
                "started_at": None,
                "completed_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        self.append_worker_event(
            int(row["id"]),
            "worker_run_queued",
            {
                "sessionId": session_id,
                "parentRunId": parent_run_id,
                "taskId": task_id,
                "workerType": worker_type,
                "workerRef": worker_ref,
            },
        )
        return row, False

    def get_worker_run(self, worker_run_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._worker_run_table).where(
                self._worker_run_table.c.id == worker_run_id,
                self._worker_run_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_worker_run_by_idempotency(self, idempotency_key: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._worker_run_table).where(
                self._worker_run_table.c.idempotency_key == idempotency_key,
                self._worker_run_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def get_worker_run_for_task(self, parent_run_id: int, task_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._worker_run_table).where(
                self._worker_run_table.c.parent_run_id == parent_run_id,
                self._worker_run_table.c.task_id == task_id,
                self._worker_run_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def mark_worker_running(self, worker_run_id: int) -> dict[str, Any] | None:
        run = self.get_worker_run(worker_run_id)
        if run is None or str(run["status"]) in _TERMINAL_WORKER_STATUSES:
            return run
        if str(run["status"]) == "RUNNING":
            return run
        now = datetime.now()
        self._session.execute(
            self._worker_run_table.update()
            .where(
                self._worker_run_table.c.id == worker_run_id,
                self._worker_run_table.c.deleted.is_(False),
                self._worker_run_table.c.status.not_in(_TERMINAL_WORKER_STATUSES),
            )
            .values(status="RUNNING", started_at=now, updated_at=now)
        )
        self._session.commit()
        self.append_worker_event(worker_run_id, "worker_run_started", {"workerRunId": _worker_run_public_id(worker_run_id)})
        return self.get_worker_run(worker_run_id)

    def complete_worker_run(
        self,
        worker_run_id: int,
        *,
        status: str,
        result_payload: dict[str, Any] | None = None,
        error: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        if status not in _TERMINAL_WORKER_STATUSES:
            raise ValueError(f"Worker status is not terminal: {status}")
        now = datetime.now()
        self._session.execute(
            self._worker_run_table.update()
            .where(
                self._worker_run_table.c.id == worker_run_id,
                self._worker_run_table.c.deleted.is_(False),
                self._worker_run_table.c.status.not_in(_TERMINAL_WORKER_STATUSES),
            )
            .values(
                status=status,
                result_payload=_redact_payload(result_payload or {}),
                error_json=_redact_payload(error or {}),
                completed_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        self.append_worker_event(
            worker_run_id,
            "worker_run_completed" if status == "COMPLETED" else f"worker_run_{status.lower()}",
            {"workerRunId": _worker_run_public_id(worker_run_id), "status": status},
        )
        return self.get_worker_run(worker_run_id)

    def append_worker_event(
        self,
        worker_run_id: int,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        visibility: str = "debug",
        source: str = "customer_assistant_worker",
        actor: str = "system",
    ) -> dict[str, Any]:
        for attempt in range(_SEQUENCE_RETRY_ATTEMPTS):
            now = datetime.now()
            sequence = self._next_worker_event_sequence(worker_run_id)
            try:
                row = insert_and_fetch(
                    self._session,
                    self._worker_event_table,
                    {
                        "worker_run_id": worker_run_id,
                        "sequence": sequence,
                        "type": event_type,
                        "visibility": visibility,
                        "source": source,
                        "actor": actor,
                        "payload": _redact_payload(payload or {}),
                        "deleted": False,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                self._session.commit()
                return row
            except sa.exc.IntegrityError as exc:
                self._session.rollback()
                if attempt == _SEQUENCE_RETRY_ATTEMPTS - 1 or not _is_sequence_conflict(exc):
                    raise
        raise RuntimeError("Could not append customer assistant worker event after sequence retries")

    def list_worker_events(self, worker_run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._worker_event_table)
            .where(
                self._worker_event_table.c.worker_run_id == worker_run_id,
                self._worker_event_table.c.deleted.is_(False),
            )
            .order_by(self._worker_event_table.c.sequence.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_worker_events_after(self, worker_run_id: int, after_sequence: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._worker_event_table)
            .where(
                self._worker_event_table.c.worker_run_id == worker_run_id,
                self._worker_event_table.c.sequence > after_sequence,
                self._worker_event_table.c.deleted.is_(False),
            )
            .order_by(self._worker_event_table.c.sequence.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def upsert_proposed_action(
        self,
        session_id: int,
        run_id: int,
        task_id: int | None,
        action_key: str,
        action_type: str,
        title: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        existing = self._session.execute(
            sa.select(self._action_table).where(
                self._action_table.c.session_id == session_id,
                self._action_table.c.action_key == action_key,
                self._action_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        if existing:
            return dict(existing)
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._action_table,
            {
                "session_id": session_id,
                "run_id": run_id,
                "task_id": task_id,
                "action_key": action_key,
                "action_type": action_type,
                "title": title,
                "payload": payload,
                "status": "PENDING",
                "result_json": {},
                "confirmed_at": None,
                "rejected_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_proposed_actions(self, session_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._action_table)
            .where(
                self._action_table.c.session_id == session_id,
                self._action_table.c.deleted.is_(False),
            )
            .order_by(self._action_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def update_proposed_action_status(
        self,
        action_id: int,
        status: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        values: dict[str, Any] = {"status": status, "updated_at": now}
        if status == "CONFIRMED":
            values["confirmed_at"] = now
        if status == "REJECTED":
            values["rejected_at"] = now
        if result is not None:
            values["result_json"] = result
        self._session.execute(
            self._action_table.update()
            .where(self._action_table.c.id == action_id, self._action_table.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        row = self._session.execute(
            sa.select(self._action_table).where(
                self._action_table.c.id == action_id,
                self._action_table.c.deleted.is_(False),
            )
        ).mappings().one()
        return dict(row)

    def transition_proposed_action_status(
        self,
        action_id: int,
        *,
        expected_status: str,
        next_status: str,
        result: dict[str, Any] | None = None,
    ) -> dict[str, Any] | None:
        now = datetime.now()
        values: dict[str, Any] = {"status": next_status, "updated_at": now}
        if next_status == "CONFIRMED":
            values["confirmed_at"] = now
        if next_status == "REJECTED":
            values["rejected_at"] = now
        if result is not None:
            values["result_json"] = result
        update_result = self._session.execute(
            self._action_table.update()
            .where(
                self._action_table.c.id == action_id,
                self._action_table.c.status == expected_status,
                self._action_table.c.deleted.is_(False),
            )
            .values(**values)
        )
        self._session.commit()
        if update_result.rowcount == 0:
            return None
        row = self._session.execute(
            sa.select(self._action_table).where(
                self._action_table.c.id == action_id,
                self._action_table.c.deleted.is_(False),
            )
        ).mappings().one()
        return dict(row)

    def update_proposed_action(
        self,
        action_id: int,
        *,
        title: str | None = None,
        payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        values: dict[str, Any] = {"updated_at": now}
        if title is not None:
            values["title"] = title
        if payload is not None:
            values["payload"] = _redact_payload(payload)
        self._session.execute(
            self._action_table.update()
            .where(self._action_table.c.id == action_id, self._action_table.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        row = self._session.execute(
            sa.select(self._action_table).where(
                self._action_table.c.id == action_id,
                self._action_table.c.deleted.is_(False),
            )
        ).mappings().one()
        return dict(row)

    def get_proposed_action(self, action_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._action_table).where(
                self._action_table.c.id == action_id,
                self._action_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def _ensure_tables(self) -> None:
        bind = self._session.get_bind()
        if bind is not None:
            Base.metadata.create_all(bind=bind, tables=customer_assistant_tables())
            self._ensure_event_actor_column(bind)

    def _ensure_event_actor_column(self, bind: Any) -> None:
        inspector = sa.inspect(bind)
        if "customer_assistant_event" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("customer_assistant_event")}
        if "actor" in columns:
            return
        with bind.begin() as connection:
            connection.execute(
                sa.text(
                    "ALTER TABLE customer_assistant_event "
                    "ADD COLUMN actor VARCHAR(30) NOT NULL DEFAULT 'customer'"
                )
            )

    def _next_event_sequence(self, session_id: int) -> int:
        value = self._session.execute(
            sa.select(sa.func.max(self._event_table.c.sequence)).where(
                self._event_table.c.session_id == session_id,
                self._event_table.c.deleted.is_(False),
            )
        ).scalar_one_or_none()
        return int(value or 0) + 1

    def _next_worker_event_sequence(self, worker_run_id: int) -> int:
        value = self._session.execute(
            sa.select(sa.func.max(self._worker_event_table.c.sequence)).where(
                self._worker_event_table.c.worker_run_id == worker_run_id,
                self._worker_event_table.c.deleted.is_(False),
            )
        ).scalar_one_or_none()
        return int(value or 0) + 1

    @staticmethod
    def _short_id(task_key: str) -> str:
        normalized = "".join(part[:2].upper() for part in task_key.split("_") if part)
        return normalized[:8] or "TASK"


_TERMINAL_WORKER_STATUSES = {"COMPLETED", "FAILED", "TIMED_OUT", "CANCELLED", "CANCEL_UNSUPPORTED"}
_SECRET_KEYS = {"api_key", "apikey", "authorization", "password", "secret", "token", "credential", "credentials"}


def _worker_run_public_id(worker_run_id: int) -> str:
    return f"customer-assistant-worker-run-{worker_run_id}"


def _is_sequence_conflict(exc: sa.exc.IntegrityError) -> bool:
    message = str(exc.orig).lower()
    return "sequence" in message and (
        "customer_assistant_event" in message or "customer_assistant_worker_event" in message
    )


def _redact_payload(value: Any) -> Any:
    if isinstance(value, dict):
        redacted: dict[str, Any] = {}
        for key, item in value.items():
            if str(key).lower() in _SECRET_KEYS:
                redacted[str(key)] = "[REDACTED]"
            else:
                redacted[str(key)] = _redact_payload(item)
        return redacted
    if isinstance(value, list):
        return [_redact_payload(item) for item in value]
    return value
