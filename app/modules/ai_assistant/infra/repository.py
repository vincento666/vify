from __future__ import annotations

from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.modules.ai_assistant.infra.schema import register_ai_assistant_tables


class IdempotencyConflict(RuntimeError):
    pass


def _resource_lock_mutex_name(resource_key: str) -> str:
    digest = sha256(resource_key.encode("utf-8")).hexdigest()[:32]
    return f"ai_assistant_resource_lock:{digest}"


def _rowcount(result: Any) -> int:
    return int(getattr(result, "rowcount", 0) or 0)


class AiAssistantRepository:
    def __init__(self, session: Session) -> None:
        register_ai_assistant_tables()
        self._session = session
        self._session_table = Base.metadata.tables["ai_assistant_session"]
        self._run_table = Base.metadata.tables["ai_assistant_run"]
        self._message_table = Base.metadata.tables["ai_assistant_message"]
        self._event_table = Base.metadata.tables["ai_assistant_event"]
        self._tool_call_table = Base.metadata.tables["ai_assistant_tool_call"]
        self._approval_table = Base.metadata.tables["ai_assistant_approval"]
        self._proposed_action_table = Base.metadata.tables["ai_assistant_proposed_action"]
        self._resource_lock_table = Base.metadata.tables["ai_assistant_resource_lock"]
        self._tool_operation_table = Base.metadata.tables["ai_assistant_tool_operation"]
        self._tool_attempt_table = Base.metadata.tables["ai_assistant_tool_attempt"]
        self._tool_operation_release_table = Base.metadata.tables["ai_assistant_tool_operation_release"]

    def create_tool_operation(
        self,
        *,
        operation_id: str,
        session_id: int,
        run_id: int,
        plan_step_id: str,
        tool_name: str,
        effect_class: str,
        idempotency_key: str | None,
        request_hash: str,
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._tool_operation_table,
            {
                "operation_id": operation_id,
                "session_id": session_id,
                "run_id": run_id,
                "plan_step_id": plan_step_id,
                "tool_name": tool_name,
                "effect_class": effect_class,
                "idempotency_key": idempotency_key,
                "request_hash": request_hash,
                "status": "PENDING",
                "response_hash": None,
                "output_payload": None,
                "completed_at": None,
                "retention_until": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def create_or_get_tool_operation(
        self,
        **values: Any,
    ) -> tuple[dict[str, Any], bool]:
        operation_id = str(values["operation_id"])
        existing = self.get_tool_operation(operation_id)
        if existing is not None:
            return existing, True
        try:
            return self.create_tool_operation(**values), False
        except sa.exc.IntegrityError:
            self._session.rollback()
            existing = self.get_tool_operation(operation_id)
            if existing is None:
                raise
            return existing, True

    def get_tool_operation(self, operation_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._tool_operation_table).where(
                self._tool_operation_table.c.operation_id == operation_id,
                self._tool_operation_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def claim_tool_operation(
        self,
        operation_id: str,
        *,
        expected_status: str,
        next_status: str,
    ) -> dict[str, Any] | None:
        result = self._session.execute(
            self._tool_operation_table.update()
            .where(
                self._tool_operation_table.c.operation_id == operation_id,
                self._tool_operation_table.c.status == expected_status,
                self._tool_operation_table.c.deleted.is_(False),
            )
            .values(status=next_status, updated_at=datetime.now())
        )
        self._session.commit()
        if not _rowcount(result):
            return None
        return self.get_tool_operation(operation_id)

    def complete_tool_operation(
        self,
        operation_id: str,
        *,
        output_payload: dict[str, Any],
        response_hash: str | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._tool_operation_table.update()
            .where(
                self._tool_operation_table.c.operation_id == operation_id,
                self._tool_operation_table.c.deleted.is_(False),
            )
            .values(
                status="COMPLETED",
                output_payload=output_payload,
                response_hash=response_hash,
                completed_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        updated = self.get_tool_operation(operation_id)
        if updated is None:
            raise KeyError(f"AI Assistant tool operation disappeared: {operation_id}")
        return updated

    def mark_tool_operation_unknown(self, operation_id: str, *, retention_until: datetime) -> dict[str, Any]:
        self._session.execute(
            self._tool_operation_table.update()
            .where(
                self._tool_operation_table.c.operation_id == operation_id,
                self._tool_operation_table.c.deleted.is_(False),
            )
            .values(status="UNKNOWN", retention_until=retention_until, updated_at=datetime.now())
        )
        self._session.commit()
        updated = self.get_tool_operation(operation_id)
        if updated is None:
            raise KeyError(f"AI Assistant tool operation disappeared: {operation_id}")
        return updated

    def release_tool_operation(
        self,
        operation_id: str,
        *,
        authority: str,
        actor: str,
        reason: str,
        evidence_ref: str,
        next_status: str,
    ) -> dict[str, Any]:
        if authority not in {"operator", "deterministic_adapter", "test_fixture"}:
            raise PermissionError(f"UNKNOWN release authority is not allowed: {authority}")
        if next_status not in {"SUCCEEDED", "FAILED", "COMPENSATED"}:
            raise ValueError(f"UNKNOWN release target is invalid: {next_status}")
        current = self.get_tool_operation(operation_id)
        if current is None:
            raise KeyError(f"AI Assistant tool operation disappeared: {operation_id}")
        if current["status"] != "UNKNOWN":
            raise ValueError(f"Only UNKNOWN operations may be released: {operation_id}")
        now = datetime.now()
        result = self._session.execute(
            self._tool_operation_table.update()
            .where(
                self._tool_operation_table.c.operation_id == operation_id,
                self._tool_operation_table.c.status == "UNKNOWN",
                self._tool_operation_table.c.deleted.is_(False),
            )
            .values(status=next_status, completed_at=now, updated_at=now)
        )
        if not _rowcount(result):
            self._session.rollback()
            raise ValueError(f"UNKNOWN operation release conflicted: {operation_id}")
        insert_and_fetch(
            self._session,
            self._tool_operation_release_table,
            {
                "operation_id": operation_id,
                "authority": authority,
                "actor": actor,
                "reason": reason,
                "evidence_ref": evidence_ref,
                "previous_status": "UNKNOWN",
                "next_status": next_status,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        released = self.get_tool_operation(operation_id)
        if released is None:
            raise KeyError(f"AI Assistant tool operation disappeared: {operation_id}")
        return released

    def list_tool_operation_releases(self, operation_id: str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._tool_operation_release_table)
            .where(self._tool_operation_release_table.c.operation_id == operation_id)
            .order_by(self._tool_operation_release_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def export_tool_operation_audit(self, operation_id: str) -> dict[str, Any]:
        operation = self.get_tool_operation(operation_id)
        if operation is None:
            raise KeyError(f"AI Assistant tool operation disappeared: {operation_id}")
        return {
            "operation": operation,
            "attempts": self.list_tool_attempts(operation_id),
            "releases": self.list_tool_operation_releases(operation_id),
        }

    def create_tool_attempt(
        self,
        *,
        operation_id: str,
        attempt_id: str,
        adapter_name: str,
        status: str,
        request_hash: str,
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._tool_attempt_table,
            {
                "operation_id": operation_id,
                "attempt_id": attempt_id,
                "adapter_name": adapter_name,
                "status": status,
                "request_hash": request_hash,
                "response_hash": None,
                "error_class": None,
                "started_at": now,
                "completed_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_tool_attempts(self, operation_id: str) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._tool_attempt_table)
            .where(
                self._tool_attempt_table.c.operation_id == operation_id,
                self._tool_attempt_table.c.deleted.is_(False),
            )
            .order_by(self._tool_attempt_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_tool_attempt(self, attempt_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._tool_attempt_table).where(
                self._tool_attempt_table.c.attempt_id == attempt_id,
                self._tool_attempt_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_tool_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        response_hash: str | None = None,
        error_class: str | None = None,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {
            "status": status,
            "response_hash": response_hash,
            "error_class": error_class,
            "updated_at": datetime.now(),
        }
        if status in {"COMPLETED", "FAILED", "UNKNOWN"}:
            values["completed_at"] = datetime.now()
        self._session.execute(
            self._tool_attempt_table.update()
            .where(
                self._tool_attempt_table.c.attempt_id == attempt_id,
                self._tool_attempt_table.c.deleted.is_(False),
            )
            .values(**values)
        )
        self._session.commit()
        updated = self.get_tool_attempt(attempt_id)
        if updated is None:
            raise KeyError(f"AI Assistant tool attempt disappeared: {attempt_id}")
        return updated

    def create_session(self, title: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._session_table,
            {
                "title": title,
                "status": "ACTIVE",
                "context_json": context or {},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_sessions(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._session_table)
            .where(self._session_table.c.deleted.is_(False))
            .order_by(self._session_table.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._session_table).where(
                self._session_table.c.id == session_id,
                self._session_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def update_session_context(self, session_id: int, context: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._session_table.update()
            .where(self._session_table.c.id == session_id, self._session_table.c.deleted.is_(False))
            .values(context_json=context, updated_at=now)
        )
        self._session.commit()
        updated = self.get_session(session_id)
        if updated is None:
            raise KeyError(f"AI Assistant session disappeared: {session_id}")
        return updated

    def clear_session_history(self, session_id: int) -> bool:
        if self.get_session(session_id) is None:
            return False
        now = datetime.now()
        for table in [
            self._run_table,
            self._message_table,
            self._event_table,
            self._tool_call_table,
            self._approval_table,
            self._proposed_action_table,
        ]:
            self._session.execute(
                table.update()
                .where(table.c.session_id == session_id, table.c.deleted.is_(False))
                .values(deleted=True, updated_at=now)
            )
        self._session.execute(
            self._session_table.update()
            .where(self._session_table.c.id == session_id, self._session_table.c.deleted.is_(False))
            .values(status="ACTIVE", context_json={}, updated_at=now)
        )
        self._session.commit()
        return True

    def delete_session(self, session_id: int) -> bool:
        if self.get_session(session_id) is None:
            return False
        self.clear_session_history(session_id)
        now = datetime.now()
        self._session.execute(
            self._session_table.update()
            .where(self._session_table.c.id == session_id, self._session_table.c.deleted.is_(False))
            .values(deleted=True, updated_at=now)
        )
        self._session.commit()
        return True

    def create_run(
        self,
        *,
        session_id: int,
        user_message: str,
        idempotency_key: str | None,
        request_hash: str | None = None,
    ) -> dict[str, Any]:
        run, _replayed = self.create_or_replay_run(
            session_id=session_id,
            user_message=user_message,
            idempotency_key=idempotency_key,
            request_hash=request_hash,
        )
        return run

    def create_or_replay_run(
        self,
        *,
        session_id: int,
        user_message: str,
        idempotency_key: str | None,
        request_hash: str | None = None,
    ) -> tuple[dict[str, Any], bool]:
        resolved_hash = request_hash or user_message
        if idempotency_key:
            existing = self.get_run_by_idempotency(session_id, idempotency_key)
            if existing is not None:
                if existing["request_hash"] != resolved_hash:
                    raise IdempotencyConflict("Idempotency key reused with different request")
                return existing, True
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._run_table,
            {
                "session_id": session_id,
                "idempotency_key": idempotency_key,
                "request_hash": resolved_hash,
                "status": "RUNNING",
                "input_payload": {"message": user_message},
                "response_payload": None,
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

    def update_run_input_payload(self, run_id: int, input_payload: dict[str, Any]) -> dict[str, Any]:
        existing = self.get_run(run_id)
        if existing is None:
            raise KeyError(f"AI Assistant run disappeared: {run_id}")
        values: dict[str, Any] = {"input_payload": input_payload, "updated_at": datetime.now()}
        response_payload = existing.get("response_payload")
        if isinstance(response_payload, dict) and "plan" in input_payload:
            values["response_payload"] = {**response_payload, "plan": input_payload["plan"]}
        self._session.execute(
            self._run_table.update()
            .where(self._run_table.c.id == run_id, self._run_table.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        updated = self.get_run(run_id)
        if updated is None:
            raise KeyError(f"AI Assistant run disappeared: {run_id}")
        return updated

    def update_run_status(
        self,
        run_id: int,
        status: str,
        *,
        response_payload: dict[str, Any] | None = None,
        completed: bool = False,
    ) -> dict[str, Any]:
        values: dict[str, Any] = {"status": status, "updated_at": datetime.now()}
        if response_payload is not None:
            values["response_payload"] = response_payload
        if completed:
            values["completed_at"] = datetime.now()
        self._session.execute(
            self._run_table.update()
            .where(self._run_table.c.id == run_id, self._run_table.c.deleted.is_(False))
            .values(**values)
        )
        self._session.commit()
        updated = self.get_run(run_id)
        if updated is None:
            raise KeyError(f"AI Assistant run disappeared: {run_id}")
        return updated

    def claim_run_status(
        self,
        run_id: int,
        *,
        expected_status: str,
        next_status: str,
        input_payload: dict[str, Any],
    ) -> dict[str, Any] | None:
        now = datetime.now()
        result = self._session.execute(
            self._run_table.update()
            .where(
                self._run_table.c.id == run_id,
                self._run_table.c.status == expected_status,
                self._run_table.c.deleted.is_(False),
            )
            .values(status=next_status, input_payload=input_payload, updated_at=now)
        )
        self._session.commit()
        if not _rowcount(result):
            return None
        updated = self.get_run(run_id)
        if updated is None:
            raise KeyError(f"AI Assistant run disappeared: {run_id}")
        return updated

    def list_session_runs(self, session_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._run_table)
            .where(
                self._run_table.c.session_id == session_id,
                self._run_table.c.deleted.is_(False),
            )
            .order_by(self._run_table.c.id.desc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def complete_run(self, run_id: int, response_payload: dict[str, Any], status: str = "COMPLETED") -> dict[str, Any]:
        now = datetime.now()
        protected_terminal_statuses = tuple({"CANCELLED", "COMPLETED", "FAILED", "DENIED"} - {status})
        self._session.execute(
            self._run_table.update()
            .where(
                self._run_table.c.id == run_id,
                self._run_table.c.deleted.is_(False),
                self._run_table.c.status.not_in(protected_terminal_statuses),
            )
            .values(
                status=status,
                response_payload=response_payload,
                completed_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        updated = self.get_run(run_id)
        if updated is None:
            raise KeyError(f"AI Assistant run disappeared: {run_id}")
        return updated

    def append_message(self, session_id: int, role: str, content: str, run_id: int | None = None) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._message_table,
            {
                "session_id": session_id,
                "run_id": run_id,
                "role": role,
                "content": content,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_run_messages(self, run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._message_table)
            .where(
                self._message_table.c.run_id == run_id,
                self._message_table.c.deleted.is_(False),
            )
            .order_by(self._message_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def append_event(
        self,
        *,
        run_id: int,
        session_id: int,
        event_type: str,
        visible_title: str,
        visible_summary: str,
        payload: dict[str, Any] | None = None,
        status: str = "COMPLETED",
        level: str = "info",
        task_id: int | None = None,
        tool_call_id: int | None = None,
        correlation_ids: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        self._lock_run_for_event_sequence(run_id)
        row = insert_and_fetch(
            self._session,
            self._event_table,
            {
                "session_id": session_id,
                "run_id": run_id,
                "task_id": task_id,
                "tool_call_id": tool_call_id,
                "sequence": self._next_event_sequence(run_id),
                "type": event_type,
                "level": level,
                "status": status,
                "visible_title": visible_title,
                "visible_summary": visible_summary,
                "payload": payload or {},
                "correlation_ids": correlation_ids or {},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_run_events(self, run_id: int, after_sequence: int = 0) -> list[dict[str, Any]]:
        if after_sequence:
            self._session.rollback()
        where = [
            self._event_table.c.run_id == run_id,
            self._event_table.c.deleted.is_(False),
        ]
        if after_sequence > 0:
            where.append(self._event_table.c.sequence > after_sequence)
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(*where)
            .order_by(self._event_table.c.sequence.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def record_tool_call(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        input_payload: dict[str, Any],
        output_payload: dict[str, Any],
        status: str,
        duration_ms: int,
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._tool_call_table,
            {
                "session_id": session_id,
                "run_id": run_id,
                "tool_name": tool_name,
                "input_payload": input_payload,
                "output_payload": output_payload,
                "status": status,
                "duration_ms": duration_ms,
                "started_at": now,
                "completed_at": now,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_run_tool_calls(self, run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._tool_call_table)
            .where(self._tool_call_table.c.run_id == run_id, self._tool_call_table.c.deleted.is_(False))
            .order_by(self._tool_call_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def create_approval(
        self,
        *,
        run_id: int,
        session_id: int,
        tool_name: str,
        risk_level: str,
        input_payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._approval_table,
            {
                "session_id": session_id,
                "run_id": run_id,
                "tool_name": tool_name,
                "risk_level": risk_level,
                "input_payload": input_payload,
                "status": "PENDING",
                "decided_by": None,
                "decision_reason": None,
                "decided_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._approval_table)
            .where(
                self._approval_table.c.status == "PENDING",
                self._approval_table.c.deleted.is_(False),
            )
            .order_by(self._approval_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def list_run_approvals(self, run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._approval_table)
            .where(
                self._approval_table.c.run_id == run_id,
                self._approval_table.c.deleted.is_(False),
            )
            .order_by(self._approval_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_approval(self, approval_id: int) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._approval_table).where(
                self._approval_table.c.id == approval_id,
                self._approval_table.c.deleted.is_(False),
            )
        ).mappings().one_or_none()
        return dict(row) if row else None

    def decide_approval(self, approval_id: int, status: str, actor_id: str, reason: str = "") -> dict[str, Any]:
        now = datetime.now()
        self._session.execute(
            self._approval_table.update()
            .where(
                self._approval_table.c.id == approval_id,
                self._approval_table.c.deleted.is_(False),
            )
            .values(
                status=status,
                decided_by=actor_id,
                decision_reason=reason,
                decided_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        updated = self.get_approval(approval_id)
        if updated is None:
            raise KeyError(f"AI Assistant approval disappeared: {approval_id}")
        return updated

    def cancel_pending_approvals_for_run(self, run_id: int, actor_id: str, reason: str = "") -> int:
        now = datetime.now()
        result = self._session.execute(
            self._approval_table.update()
            .where(
                self._approval_table.c.run_id == run_id,
                self._approval_table.c.status == "PENDING",
                self._approval_table.c.deleted.is_(False),
            )
            .values(
                status="CANCELLED",
                decided_by=actor_id,
                decision_reason=reason,
                decided_at=now,
                updated_at=now,
            )
        )
        self._session.commit()
        return _rowcount(result)

    def cancel_pending_proposed_actions_for_run(self, run_id: int) -> int:
        now = datetime.now()
        result = self._session.execute(
            self._proposed_action_table.update()
            .where(
                self._proposed_action_table.c.run_id == run_id,
                self._proposed_action_table.c.status == "PENDING",
                self._proposed_action_table.c.deleted.is_(False),
            )
            .values(status="CANCELLED", updated_at=now)
        )
        self._session.commit()
        return _rowcount(result)

    def create_proposed_action(
        self,
        *,
        run_id: int,
        session_id: int,
        approval_id: int,
        action_type: str,
        title: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._proposed_action_table,
            {
                "session_id": session_id,
                "run_id": run_id,
                "approval_id": approval_id,
                "action_type": action_type,
                "title": title,
                "payload": payload,
                "status": "PENDING",
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def acquire_resource_lock(
        self,
        *,
        resource_key: str,
        mode: str,
        owner_session_id: int,
        owner_run_id: int,
        owner_tool_call_id: int | None,
        ttl_seconds: int,
    ) -> dict[str, Any]:
        now = datetime.now()
        requested_mode = mode.upper()
        mutex_name = _resource_lock_mutex_name(resource_key)
        if not self._try_get_mysql_lock(mutex_name):
            return {
                "status": "CONTENDED",
                "resource_key": resource_key,
                "mode": requested_mode,
                "fencing_token": 0,
                "reason": f"resource {resource_key} lock acquisition is already in progress",
            }
        try:
            self._expire_resource_locks(now)
            active_rows = self._session.execute(
                sa.select(self._resource_lock_table)
                .where(
                    self._resource_lock_table.c.resource_key == resource_key,
                    self._resource_lock_table.c.status == "ACTIVE",
                    self._resource_lock_table.c.deleted.is_(False),
                    self._resource_lock_table.c.lease_expires_at > now,
                )
                .order_by(self._resource_lock_table.c.id.asc())
            ).mappings().all()
            conflict = None
            for row in active_rows:
                active_mode = str(row["mode"]).upper()
                if requested_mode == "WRITE" or active_mode == "WRITE":
                    conflict = row
                    break
            if conflict is not None:
                self._session.commit()
                return {
                    "status": "CONTENDED",
                    "resource_key": resource_key,
                    "mode": requested_mode,
                    "fencing_token": 0,
                    "reason": f"resource {resource_key} is locked by run {conflict['owner_run_id']}",
                }
            max_token = self._session.execute(
                sa.select(sa.func.max(self._resource_lock_table.c.fencing_token)).where(
                    self._resource_lock_table.c.resource_key == resource_key,
                    self._resource_lock_table.c.deleted.is_(False),
                )
            ).scalar_one_or_none()
            inserted_row = insert_and_fetch(
                self._session,
                self._resource_lock_table,
                {
                    "resource_key": resource_key,
                    "mode": requested_mode,
                    "owner_session_id": owner_session_id,
                    "owner_run_id": owner_run_id,
                    "owner_tool_call_id": owner_tool_call_id,
                    "lease_expires_at": now + timedelta(seconds=ttl_seconds),
                    "fencing_token": int(max_token or 0) + 1,
                    "status": "ACTIVE",
                    "deleted": False,
                    "created_at": now,
                    "updated_at": now,
                },
            )
            self._session.commit()
            return {**inserted_row, "status": "ACQUIRED"}
        except Exception:
            self._session.rollback()
            raise
        finally:
            self._release_mysql_lock(mutex_name)

    def release_resource_lock(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
    ) -> bool:
        now = datetime.now()
        result = self._session.execute(
            self._resource_lock_table.update()
            .where(
                self._resource_lock_table.c.resource_key == resource_key,
                self._resource_lock_table.c.owner_session_id == owner_session_id,
                self._resource_lock_table.c.owner_run_id == owner_run_id,
                self._resource_lock_table.c.fencing_token == fencing_token,
                self._resource_lock_table.c.status == "ACTIVE",
                self._resource_lock_table.c.deleted.is_(False),
            )
            .values(status="RELEASED", updated_at=now)
        )
        self._session.commit()
        return bool(_rowcount(result))

    def renew_resource_lock(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
        ttl_seconds: int,
    ) -> bool:
        now = datetime.now()
        result = self._session.execute(
            self._resource_lock_table.update()
            .where(
                self._resource_lock_table.c.resource_key == resource_key,
                self._resource_lock_table.c.owner_session_id == owner_session_id,
                self._resource_lock_table.c.owner_run_id == owner_run_id,
                self._resource_lock_table.c.fencing_token == fencing_token,
                self._resource_lock_table.c.status == "ACTIVE",
                self._resource_lock_table.c.deleted.is_(False),
                self._resource_lock_table.c.lease_expires_at > now,
            )
            .values(lease_expires_at=now + timedelta(seconds=ttl_seconds), updated_at=now)
        )
        self._session.commit()
        return bool(_rowcount(result))

    def _expire_resource_locks(self, now: datetime) -> None:
        self._session.execute(
            self._resource_lock_table.update()
            .where(
                self._resource_lock_table.c.status == "ACTIVE",
                self._resource_lock_table.c.deleted.is_(False),
                self._resource_lock_table.c.lease_expires_at <= now,
            )
            .values(status="EXPIRED", updated_at=now)
        )

    def _try_get_mysql_lock(self, name: str) -> bool:
        value = self._session.execute(sa.text("SELECT GET_LOCK(:name, 0)"), {"name": name}).scalar_one_or_none()
        return int(value or 0) == 1

    def _release_mysql_lock(self, name: str) -> None:
        try:
            self._session.execute(sa.text("SELECT RELEASE_LOCK(:name)"), {"name": name})
            self._session.commit()
        except Exception:
            self._session.rollback()

    def _next_event_sequence(self, run_id: int) -> int:
        current = self._session.execute(
            sa.select(sa.func.max(self._event_table.c.sequence)).where(
                self._event_table.c.run_id == run_id,
                self._event_table.c.deleted.is_(False),
            )
        ).scalar_one_or_none()
        return int(current or 0) + 1

    def _lock_run_for_event_sequence(self, run_id: int) -> None:
        self._session.execute(
            sa.select(self._run_table.c.id)
            .where(
                self._run_table.c.id == run_id,
                self._run_table.c.deleted.is_(False),
            )
            .with_for_update()
        ).scalar_one_or_none()
