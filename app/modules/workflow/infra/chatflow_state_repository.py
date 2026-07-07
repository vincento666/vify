from __future__ import annotations

from datetime import datetime, timedelta
import threading
from typing import Any

import sqlalchemy as sa
from sqlalchemy.orm import Session

from app.core.database import Base
from app.core.db_write import insert_and_fetch
from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.realtime.redis_streams import RuntimeEventStreamBus, normalize_runtime_stream_event

register_baseline_tables()


_SEQUENCE_RETRY_ATTEMPTS = 3
_CHATFLOW_RUNTIME_EVENT_SOURCE = "chatflow_runtime_v2"
_EVENT_SEQUENCE_LOCKS: dict[int, threading.Lock] = {}
_EVENT_SEQUENCE_LOCKS_GUARD = threading.Lock()
_HIGH_FREQUENCY_EVENT_TYPES = {"llm_delta", "agent_delta", "node_progress", "tool_delta", "token_delta"}
_COMPACTED_EVENT_TYPE = "runtime_event_summary"
_COMPACTION_KEEP_FIRST = 5
_COMPACTION_SAMPLE_INTERVAL = 3


def _chatflow_event_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    event_payload = dict(payload or {})
    event_payload.setdefault("ownerType", "CHATFLOW")
    event_payload.setdefault("source", _CHATFLOW_RUNTIME_EVENT_SOURCE)
    return event_payload


class ChatflowStateRepository:
    def __init__(self, session: Session, event_stream_bus: RuntimeEventStreamBus | None = None) -> None:
        self._session = session
        self._event_stream_bus = event_stream_bus
        self._session_table = Base.metadata.tables["chatflow_session"]
        self._event_table = Base.metadata.tables["chatflow_event"]
        self._event_outbox_table = Base.metadata.tables["runtime_event_outbox"]
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
        with _event_sequence_lock(run_id):
            for attempt in range(_SEQUENCE_RETRY_ATTEMPTS):
                now = datetime.now()
                event_type_to_store, payload_to_store, persist = self._compact_event(
                    run_id=run_id,
                    event_type=event_type,
                    node_key=node_key,
                    payload=payload,
                )
                if not persist:
                    return {
                        "id": 0,
                        "session_id": session_id,
                        "chatflow_id": chatflow_id,
                        "run_id": run_id,
                        "sequence": max(0, self._next_sequence(run_id) - 1),
                        "event_type": event_type,
                        "node_key": node_key,
                        "payload": _chatflow_event_payload(payload_to_store),
                        "checkpoint_id": checkpoint_id,
                        "deleted": False,
                        "created_at": now,
                        "updated_at": now,
                    }
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
                            "event_type": event_type_to_store,
                            "node_key": node_key,
                            "payload": _chatflow_event_payload(payload_to_store),
                            "checkpoint_id": checkpoint_id,
                            "deleted": False,
                            "created_at": now,
                            "updated_at": now,
                        },
                    )
                    outbox = self._create_event_outbox(row)
                    self._session.commit()
                    self._publish_event(row, outbox_id=int(outbox["id"]) if outbox else None)
                    return row
                except sa.exc.IntegrityError as exc:
                    self._session.rollback()
                    if attempt == _SEQUENCE_RETRY_ATTEMPTS - 1 or not _is_sequence_conflict(exc):
                        raise
        raise RuntimeError("Could not append chatflow event after sequence retries")

    def _compact_event(
        self,
        *,
        run_id: int,
        event_type: str,
        node_key: str,
        payload: dict[str, Any] | None,
    ) -> tuple[str, dict[str, Any], bool]:
        if event_type not in _HIGH_FREQUENCY_EVENT_TYPES:
            return event_type, dict(payload or {}), True
        attempted = self._compacted_attempt_count(run_id=run_id, event_type=event_type, node_key=node_key)
        if attempted < _COMPACTION_KEEP_FIRST:
            return event_type, dict(payload or {}), True
        sampled_count = attempted - _COMPACTION_KEEP_FIRST + 1
        summary_payload = {
            "compactedEventType": event_type,
            "sampledCount": sampled_count,
            "latestPayload": dict(payload or {}),
            "compaction": {
                "keepFirst": _COMPACTION_KEEP_FIRST,
                "sampleInterval": _COMPACTION_SAMPLE_INTERVAL,
            },
        }
        should_persist = sampled_count == 1 or sampled_count % _COMPACTION_SAMPLE_INTERVAL == 1
        if not should_persist:
            self._update_latest_compaction_summary(
                run_id=run_id,
                event_type=event_type,
                node_key=node_key,
                payload=summary_payload,
            )
        return _COMPACTED_EVENT_TYPE, summary_payload, should_persist

    def _compacted_attempt_count(self, *, run_id: int, event_type: str, node_key: str) -> int:
        rows = self._session.execute(
            sa.select(self._event_table.c.event_type, self._event_table.c.payload)
            .where(
                self._event_table.c.run_id == run_id,
                self._event_table.c.node_key == node_key,
                self._event_table.c.event_type.in_((event_type, _COMPACTED_EVENT_TYPE)),
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.asc(), self._event_table.c.id.asc())
        ).mappings().all()
        original_count = 0
        compacted_count = 0
        for row in rows:
            if row["event_type"] == event_type:
                original_count += 1
                continue
            event_payload = row["payload"] if isinstance(row["payload"], dict) else {}
            if event_payload.get("compactedEventType") == event_type:
                compacted_count = max(compacted_count, int(event_payload.get("sampledCount") or 0))
        return original_count + compacted_count

    def _update_latest_compaction_summary(
        self,
        *,
        run_id: int,
        event_type: str,
        node_key: str,
        payload: dict[str, Any],
    ) -> None:
        row = self._session.execute(
            sa.select(self._event_table.c.id, self._event_table.c.payload)
            .where(
                self._event_table.c.run_id == run_id,
                self._event_table.c.node_key == node_key,
                self._event_table.c.event_type == _COMPACTED_EVENT_TYPE,
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.sequence.desc(), self._event_table.c.id.desc())
            .limit(1)
        ).mappings().first()
        if row is None:
            return
        existing = row["payload"] if isinstance(row["payload"], dict) else {}
        if existing.get("compactedEventType") != event_type:
            return
        self._session.execute(
            self._event_table.update()
            .where(self._event_table.c.id == int(row["id"]))
            .values(payload=_chatflow_event_payload(payload), updated_at=datetime.now())
        )
        self._session.commit()

    def _publish_event(self, row: dict[str, Any], *, outbox_id: int | None = None) -> None:
        if self._event_stream_bus is None:
            return
        try:
            self._event_stream_bus.publish(row)
        except Exception as exc:
            if outbox_id is not None:
                self._mark_event_outbox_failed(outbox_id, exc)
            return
        if outbox_id is not None:
            self._mark_event_outbox_published(outbox_id)

    def _create_event_outbox(self, row: dict[str, Any]) -> dict[str, Any] | None:
        if self._event_stream_bus is None:
            return None
        now = datetime.now()
        return insert_and_fetch(
            self._session,
            self._event_outbox_table,
            {
                "run_id": int(row["run_id"]),
                "event_id": int(row["id"]),
                "sequence": int(row["sequence"]),
                "status": "PENDING",
                "attempt_count": 0,
                "last_error": None,
                "payload": normalize_runtime_stream_event(row),
                "published_at": None,
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )

    def _mark_event_outbox_published(self, outbox_id: int) -> None:
        self._session.execute(
            self._event_outbox_table.update()
            .where(self._event_outbox_table.c.id == outbox_id)
            .values(
                status="PUBLISHED",
                attempt_count=self._event_outbox_table.c.attempt_count + 1,
                last_error=None,
                published_at=datetime.now(),
                updated_at=datetime.now(),
            )
        )
        self._session.commit()

    def _mark_event_outbox_failed(self, outbox_id: int, exc: Exception) -> None:
        self._session.execute(
            self._event_outbox_table.update()
            .where(self._event_outbox_table.c.id == outbox_id)
            .values(
                status="FAILED",
                attempt_count=self._event_outbox_table.c.attempt_count + 1,
                last_error=str(exc)[:1000],
                updated_at=datetime.now(),
            )
        )
        self._session.commit()

    def list_event_outbox(
        self,
        *,
        run_id: int | None = None,
        statuses: tuple[str, ...] = ("PENDING", "FAILED"),
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        conditions = [self._event_outbox_table.c.deleted.is_(False)]
        if run_id is not None:
            conditions.append(self._event_outbox_table.c.run_id == run_id)
        if statuses:
            conditions.append(self._event_outbox_table.c.status.in_(statuses))
        rows = self._session.execute(
            sa.select(self._event_outbox_table)
            .where(*conditions)
            .order_by(self._event_outbox_table.c.sequence.asc(), self._event_outbox_table.c.id.asc())
            .limit(limit)
        ).mappings().all()
        return [dict(row) for row in rows]

    def replay_event_outbox(
        self,
        *,
        event_stream_bus: RuntimeEventStreamBus,
        run_id: int | None = None,
        limit: int = 100,
    ) -> dict[str, int]:
        published = 0
        failed = 0
        rows = self.list_event_outbox(run_id=run_id, statuses=("PENDING", "FAILED"), limit=limit)
        for row in rows:
            try:
                event = row["payload"] if isinstance(row["payload"], dict) else self._event_payload_for_outbox(row)
                event_stream_bus.publish(event)
            except Exception as exc:
                failed += 1
                self._mark_event_outbox_failed(int(row["id"]), exc)
                continue
            published += 1
            self._mark_event_outbox_published(int(row["id"]))
        return {"published": published, "failed": failed}

    def _event_payload_for_outbox(self, row: dict[str, Any]) -> dict[str, Any]:
        event = self._session.execute(
            sa.select(self._event_table).where(self._event_table.c.id == int(row["event_id"]))
        ).mappings().one()
        return normalize_runtime_stream_event(dict(event))

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

    def list_session_events(
        self,
        chatflow_id: int,
        session_id: str,
        after_event_id: int = 0,
    ) -> list[dict[str, Any]]:
        rows = self._session.execute(
            sa.select(self._event_table)
            .where(
                self._event_table.c.chatflow_id == chatflow_id,
                self._event_table.c.session_id == session_id,
                self._event_table.c.id > after_event_id,
                self._event_table.c.deleted.is_(False),
            )
            .order_by(self._event_table.c.id.asc())
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


def _event_sequence_lock(run_id: int) -> threading.Lock:
    normalized_run_id = int(run_id)
    with _EVENT_SEQUENCE_LOCKS_GUARD:
        lock = _EVENT_SEQUENCE_LOCKS.get(normalized_run_id)
        if lock is None:
            lock = threading.Lock()
            _EVENT_SEQUENCE_LOCKS[normalized_run_id] = lock
        return lock
