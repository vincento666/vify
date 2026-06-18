from __future__ import annotations

from datetime import datetime
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.modules.ai_assistant.infra.schema import register_ai_assistant_tables


class IdempotencyConflict(RuntimeError):
    pass


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
        self._session.execute(
            self._run_table.update()
            .where(self._run_table.c.id == run_id, self._run_table.c.deleted.is_(False))
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

    def list_run_events(self, run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(self._event_table.c.run_id == run_id, self._event_table.c.deleted.is_(False))
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

    def _next_event_sequence(self, run_id: int) -> int:
        current = self._session.execute(
            sa.select(sa.func.max(self._event_table.c.sequence)).where(
                self._event_table.c.run_id == run_id,
                self._event_table.c.deleted.is_(False),
            )
        ).scalar_one_or_none()
        return int(current or 0) + 1
