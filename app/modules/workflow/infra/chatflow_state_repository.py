from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.realtime.redis_streams import RuntimeEventStreamBus

register_baseline_tables()


_SEQUENCE_RETRY_ATTEMPTS = 3


class ChatflowStateRepository:
    def __init__(self, session: Session, event_stream_bus: RuntimeEventStreamBus | None = None) -> None:
        self._session = session
        self._event_stream_bus = event_stream_bus
        self._session_table = Base.metadata.tables["chatflow_session"]
        self._event_table = Base.metadata.tables["chatflow_event"]
        self._checkpoint_table = Base.metadata.tables["chatflow_checkpoint"]

    def create_session(
        self,
        *,
        session_id: str,
        chatflow_id: int,
        conversation_id: str,
        user_id: str,
        channel: str,
        channel_id: str,
        status: str,
        current_run_id: int,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._session_table,
            {
                "session_id": session_id,
                "chatflow_id": chatflow_id,
                "conversation_id": conversation_id,
                "user_id": user_id,
                "channel": channel,
                "channel_id": channel_id,
                "status": status,
                "current_run_id": current_run_id,
                "variables": variables or {},
                "expires_at": now + timedelta(days=1),
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
        session_id: str,
        chatflow_id: int,
        run_id: int,
        event_type: str,
        node_key: str = "",
        payload: dict[str, Any] | None = None,
        checkpoint_id: int | None = None,
    ) -> dict[str, Any]:
        for attempt in range(_SEQUENCE_RETRY_ATTEMPTS):
            now = datetime.now()
            sequence = self._next_sequence(run_id)
            try:
                row = insert_and_fetch(
                    self._session,
                    self._event_table,
                    {
                        "session_id": session_id,
                        "chatflow_id": chatflow_id,
                        "run_id": run_id,
                        "sequence": sequence,
                        "event_type": event_type,
                        "node_key": node_key,
                        "payload": payload or {},
                        "checkpoint_id": checkpoint_id,
                        "deleted": False,
                        "created_at": now,
                        "updated_at": now,
                    },
                )
                self._session.commit()
                self._publish_event(row)
                return row
            except sa.exc.IntegrityError as exc:
                self._session.rollback()
                if attempt == _SEQUENCE_RETRY_ATTEMPTS - 1 or not _is_sequence_conflict(exc):
                    raise
        raise RuntimeError("Could not append chatflow event after sequence retries")

    def _publish_event(self, row: dict[str, Any]) -> None:
        if self._event_stream_bus is None:
            return
        try:
            self._event_stream_bus.publish(row)
        except Exception:
            return

    def create_checkpoint(
        self,
        *,
        session_id: str,
        chatflow_id: int,
        run_id: int,
        pending_node_key: str,
        execution_context: dict[str, Any],
        node_outputs: dict[str, Any],
        variable_scopes: dict[str, Any],
        resume_schema: dict[str, Any],
    ) -> dict[str, Any]:
        now = datetime.now()
        row = insert_and_fetch(
            self._session,
            self._checkpoint_table,
            {
                "session_id": session_id,
                "chatflow_id": chatflow_id,
                "run_id": run_id,
                "event_id": None,
                "pending_node_key": pending_node_key,
                "next_edge_hint": "",
                "execution_context": execution_context,
                "node_outputs": node_outputs,
                "variable_scopes": variable_scopes,
                "resume_schema": resume_schema,
                "status": "waiting",
                "expires_at": now + timedelta(days=7),
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        self._session.commit()
        return row

    def link_checkpoint_event(self, checkpoint_id: int, event_id: int) -> None:
        self._session.execute(
            self._checkpoint_table.update()
            .where(self._checkpoint_table.c.id == checkpoint_id)
            .values(event_id=event_id, updated_at=datetime.now())
        )
        self._session.commit()

    def get_session(self, chatflow_id: int, session_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._session_table)
            .where(
                self._session_table.c.chatflow_id == chatflow_id,
                self._session_table.c.session_id == session_id,
                self._session_table.c.deleted.is_(False),
            )
            .order_by(self._session_table.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def latest_waiting_event(self, chatflow_id: int, session_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.chatflow_id == chatflow_id,
                self._event_table.c.session_id == session_id,
                self._event_table.c.event_type == "interrupt",
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def latest_checkpoint(self, chatflow_id: int, session_id: str) -> dict[str, Any] | None:
        row = self._session.execute(
            sa.select(self._checkpoint_table)
            .where(
                self._checkpoint_table.c.chatflow_id == chatflow_id,
                self._checkpoint_table.c.session_id == session_id,
                self._checkpoint_table.c.status == "waiting",
                self._checkpoint_table.c.deleted.is_(False),
            )
            .order_by(self._checkpoint_table.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def get_waiting_checkpoint(
        self,
        chatflow_id: int,
        run_id: int,
        event_id: int | None = None,
    ) -> dict[str, Any] | None:
        conditions = [
            self._checkpoint_table.c.chatflow_id == chatflow_id,
            self._checkpoint_table.c.run_id == run_id,
            self._checkpoint_table.c.status == "waiting",
            self._checkpoint_table.c.deleted.is_(False),
        ]
        if event_id is not None:
            conditions.append(self._checkpoint_table.c.event_id == event_id)
        row = self._session.execute(
            sa.select(self._checkpoint_table)
            .where(*conditions)
            .order_by(self._checkpoint_table.c.id.desc())
        ).mappings().first()
        return dict(row) if row else None

    def mark_checkpoint_completed(self, checkpoint_id: int) -> None:
        self._session.execute(
            self._checkpoint_table.update()
            .where(self._checkpoint_table.c.id == checkpoint_id)
            .values(status="completed", updated_at=datetime.now())
        )
        self._session.commit()

    def update_session_status(
        self,
        *,
        chatflow_id: int,
        session_id: str,
        status: str,
        current_run_id: int,
        variables: dict[str, Any] | None = None,
    ) -> None:
        values: dict[str, Any] = {
            "status": status,
            "current_run_id": current_run_id,
            "updated_at": datetime.now(),
        }
        if variables is not None:
            values["variables"] = variables
        self._session.execute(
            self._session_table.update()
            .where(
                self._session_table.c.chatflow_id == chatflow_id,
                self._session_table.c.session_id == session_id,
                self._session_table.c.deleted.is_(False),
            )
            .values(**values)
        )
        self._session.commit()

    def list_events(self, chatflow_id: int, run_id: int) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.chatflow_id == chatflow_id,
                self._event_table.c.run_id == run_id,
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.asc(), self._event_table.c.id.asc())
        ).mappings().all()
        return [dict(row) for row in rows]

    def find_resume_event_by_idempotency_key(
        self,
        chatflow_id: int,
        run_id: int,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.chatflow_id == chatflow_id,
                self._event_table.c.run_id == run_id,
                self._event_table.c.event_type.in_(("resume", "workflow_run_resumed")),
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.asc(), self._event_table.c.id.asc())
        ).mappings().all()
        for row in rows:
            payload = row["payload"] if isinstance(row["payload"], dict) else {}
            if str(payload.get("idempotencyKey") or "") == idempotency_key:
                return dict(row)
        return None

    def find_started_run_by_idempotency_key(
        self,
        chatflow_id: int,
        idempotency_key: str,
    ) -> dict[str, Any] | None:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.chatflow_id == chatflow_id,
                self._event_table.c.event_type == "workflow_run_started",
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.asc(), self._event_table.c.id.asc())
        ).mappings().all()
        for row in rows:
            payload = row["payload"] if isinstance(row["payload"], dict) else {}
            if str(payload.get("idempotencyKey") or "") == idempotency_key:
                return dict(row)
        return None

    def recent_message_history(self, chatflow_id: int, session_id: str, limit: int = 10) -> list[dict[str, str]]:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.chatflow_id == chatflow_id,
                self._event_table.c.session_id == session_id,
                self._event_table.c.event_type == "message",
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.id.desc())
            .limit(max(1, limit))
        ).mappings().all()
        history: list[dict[str, str]] = []
        for row in reversed(rows):
            payload = row["payload"] if isinstance(row["payload"], dict) else {}
            content = str(payload.get("content") or "")
            if content:
                history.append({"role": "assistant", "content": content})
        return history

    def _next_sequence(self, run_id: int) -> int:
        value = self._session.execute(
            sa.select(sa.func.coalesce(sa.func.max(self._event_table.c.sequence), 0))
            .where(self._event_table.c.run_id == run_id)
        ).scalar_one()
        return int(value) + 1


def _is_sequence_conflict(exc: sa.exc.IntegrityError) -> bool:
    message = str(exc.orig).lower()
    return "sequence" in message and ("chatflow_event" in message or "idx_chatflow_event_run_sequence" in message)
