from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from app.modules.ai_assistant.infra.repository import IdempotencyConflict


class InMemoryAiAssistantRepository:
    def __init__(self) -> None:
        self._sessions: dict[int, dict[str, Any]] = {}
        self._runs: dict[int, dict[str, Any]] = {}
        self._messages: list[dict[str, Any]] = []
        self._events: list[dict[str, Any]] = []
        self._tool_calls: list[dict[str, Any]] = []
        self._approvals: dict[int, dict[str, Any]] = {}
        self._proposed_actions: list[dict[str, Any]] = []
        self._resource_locks: list[dict[str, Any]] = []
        self._session_id = 0
        self._run_id = 0
        self._message_id = 0
        self._event_id = 0
        self._tool_call_id = 0
        self._approval_id = 0
        self._proposed_action_id = 0
        self._resource_lock_id = 0

    def create_session(self, title: str = "", context: dict[str, Any] | None = None) -> dict[str, Any]:
        now = datetime.now()
        self._session_id += 1
        row = {
            "id": self._session_id,
            "title": title,
            "status": "ACTIVE",
            "context_json": context or {},
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }
        self._sessions[self._session_id] = row
        return dict(row)

    def list_sessions(self) -> list[dict[str, Any]]:
        return [dict(row) for row in self._sessions.values() if not row["deleted"]]

    def get_session(self, session_id: int) -> dict[str, Any] | None:
        row = self._sessions.get(session_id)
        if row is None or row["deleted"]:
            return None
        return dict(row)

    def update_session_context(self, session_id: int, context: dict[str, Any]) -> dict[str, Any]:
        row = self._sessions[session_id]
        row["context_json"] = context
        row["updated_at"] = datetime.now()
        return dict(row)

    def clear_session_history(self, session_id: int) -> bool:
        return session_id in self._sessions

    def delete_session(self, session_id: int) -> bool:
        row = self._sessions.get(session_id)
        if row is None:
            return False
        row["deleted"] = True
        row["updated_at"] = datetime.now()
        return True

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
            for row in self._runs.values():
                if row["session_id"] == session_id and row["idempotency_key"] == idempotency_key and not row["deleted"]:
                    if row["request_hash"] != resolved_hash:
                        raise IdempotencyConflict("Idempotency key reused with different request")
                    return dict(row), True
        now = datetime.now()
        self._run_id += 1
        row = {
            "id": self._run_id,
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
        }
        self._runs[row["id"]] = row
        return dict(row), False

    def get_run(self, run_id: int) -> dict[str, Any] | None:
        row = self._runs.get(run_id)
        if row is None or row["deleted"]:
            return None
        return dict(row)

    def list_session_runs(self, session_id: int) -> list[dict[str, Any]]:
        rows = [row for row in self._runs.values() if row["session_id"] == session_id and not row["deleted"]]
        return [dict(row) for row in sorted(rows, key=lambda row: row["id"], reverse=True)]

    def update_run_input_payload(self, run_id: int, input_payload: dict[str, Any]) -> dict[str, Any]:
        row = self._runs[run_id]
        row["input_payload"] = input_payload
        if isinstance(row.get("response_payload"), dict) and "plan" in input_payload:
            row["response_payload"] = {**row["response_payload"], "plan": input_payload["plan"]}
        row["updated_at"] = datetime.now()
        return dict(row)

    def complete_run(self, run_id: int, response_payload: dict[str, Any], status: str = "COMPLETED") -> dict[str, Any]:
        row = self._runs[run_id]
        row["status"] = status
        row["response_payload"] = response_payload
        row["completed_at"] = datetime.now()
        row["updated_at"] = row["completed_at"]
        return dict(row)

    def append_message(self, session_id: int, role: str, content: str, run_id: int | None = None) -> dict[str, Any]:
        self._message_id += 1
        now = datetime.now()
        row = {
            "id": self._message_id,
            "session_id": session_id,
            "run_id": run_id,
            "role": role,
            "content": content,
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }
        self._messages.append(row)
        return dict(row)

    def list_run_messages(self, run_id: int) -> list[dict[str, Any]]:
        rows = [row for row in self._messages if row["run_id"] == run_id and not row["deleted"]]
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
        self._event_id += 1
        sequence = len([row for row in self._events if row["run_id"] == run_id and not row["deleted"]]) + 1
        now = datetime.now()
        row = {
            "id": self._event_id,
            "session_id": session_id,
            "run_id": run_id,
            "task_id": task_id,
            "tool_call_id": tool_call_id,
            "sequence": sequence,
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
        }
        self._events.append(row)
        return dict(row)

    def list_run_events(self, run_id: int, after_sequence: int = 0) -> list[dict[str, Any]]:
        rows = [
            row
            for row in self._events
            if row["run_id"] == run_id and not row["deleted"] and int(row["sequence"]) > after_sequence
        ]
        return [dict(row) for row in sorted(rows, key=lambda row: row["sequence"])]

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
        self._tool_call_id += 1
        now = datetime.now()
        row = {
            "id": self._tool_call_id,
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
        }
        self._tool_calls.append(row)
        return dict(row)

    def list_run_tool_calls(self, run_id: int) -> list[dict[str, Any]]:
        rows = [row for row in self._tool_calls if row["run_id"] == run_id and not row["deleted"]]
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
        self._approval_id += 1
        now = datetime.now()
        row = {
            "id": self._approval_id,
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
        }
        self._approvals[self._approval_id] = row
        return dict(row)

    def list_run_approvals(self, run_id: int) -> list[dict[str, Any]]:
        rows = [row for row in self._approvals.values() if row["run_id"] == run_id and not row["deleted"]]
        return [dict(row) for row in rows]

    def list_pending_approvals(self) -> list[dict[str, Any]]:
        rows = [row for row in self._approvals.values() if row["status"] == "PENDING" and not row["deleted"]]
        return [dict(row) for row in rows]

    def get_approval(self, approval_id: int) -> dict[str, Any] | None:
        row = self._approvals.get(approval_id)
        if row is None or row["deleted"]:
            return None
        return dict(row)

    def decide_approval(self, approval_id: int, status: str, actor_id: str, reason: str = "") -> dict[str, Any]:
        row = self._approvals.get(approval_id)
        if row is None or row["deleted"]:
            raise KeyError(f"AI Assistant approval not found: {approval_id}")
        now = datetime.now()
        row["status"] = status
        row["decided_by"] = actor_id
        row["decision_reason"] = reason
        row["decided_at"] = now
        row["updated_at"] = now
        return dict(row)

    def create_proposed_action(
        self,
        *,
        run_id: int,
        session_id: int,
        approval_id: int | None,
        action_type: str,
        title: str,
        payload: dict[str, Any],
    ) -> dict[str, Any]:
        self._proposed_action_id += 1
        now = datetime.now()
        row = {
            "id": self._proposed_action_id,
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
        }
        self._proposed_actions.append(row)
        return dict(row)

    def cancel_pending_approvals_for_run(self, run_id: int, actor_id: str, reason: str = "") -> int:
        now = datetime.now()
        count = 0
        for row in self._approvals.values():
            if row["run_id"] == run_id and row["status"] == "PENDING" and not row["deleted"]:
                row["status"] = "CANCELLED"
                row["decided_by"] = actor_id
                row["decision_reason"] = reason
                row["decided_at"] = now
                row["updated_at"] = now
                count += 1
        return count

    def cancel_pending_proposed_actions_for_run(self, run_id: int) -> int:
        now = datetime.now()
        count = 0
        for row in self._proposed_actions:
            if row["run_id"] == run_id and row["status"] == "PENDING" and not row["deleted"]:
                row["status"] = "CANCELLED"
                row["updated_at"] = now
                count += 1
        return count

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
        self._expire_resource_locks(now)
        requested_mode = mode.upper()
        for row in self._resource_locks:
            if row["resource_key"] != resource_key or row["status"] != "ACTIVE" or row["deleted"]:
                continue
            if row["lease_expires_at"] <= now:
                continue
            active_mode = str(row["mode"]).upper()
            if requested_mode == "WRITE" or active_mode == "WRITE":
                return {
                    "status": "CONTENDED",
                    "resource_key": resource_key,
                    "mode": requested_mode,
                    "fencing_token": 0,
                    "reason": f"resource {resource_key} is locked by run {row['owner_run_id']}",
                }
        self._resource_lock_id += 1
        max_token = max(
            [int(row["fencing_token"]) for row in self._resource_locks if row["resource_key"] == resource_key],
            default=0,
        )
        row = {
            "id": self._resource_lock_id,
            "resource_key": resource_key,
            "mode": requested_mode,
            "owner_session_id": owner_session_id,
            "owner_run_id": owner_run_id,
            "owner_tool_call_id": owner_tool_call_id,
            "lease_expires_at": now + timedelta(seconds=ttl_seconds),
            "fencing_token": max_token + 1,
            "status": "ACTIVE",
            "deleted": False,
            "created_at": now,
            "updated_at": now,
        }
        self._resource_locks.append(row)
        return {**row, "status": "ACQUIRED"}

    def release_resource_lock(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
    ) -> bool:
        now = datetime.now()
        for row in self._resource_locks:
            if (
                row["resource_key"] == resource_key
                and row["owner_session_id"] == owner_session_id
                and row["owner_run_id"] == owner_run_id
                and row["fencing_token"] == fencing_token
                and row["status"] == "ACTIVE"
                and not row["deleted"]
            ):
                row["status"] = "RELEASED"
                row["updated_at"] = now
                return True
        return False

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
        for row in self._resource_locks:
            if (
                row["resource_key"] == resource_key
                and row["owner_session_id"] == owner_session_id
                and row["owner_run_id"] == owner_run_id
                and row["fencing_token"] == fencing_token
                and row["status"] == "ACTIVE"
                and row["lease_expires_at"] > now
                and not row["deleted"]
            ):
                row["lease_expires_at"] = now + timedelta(seconds=ttl_seconds)
                row["updated_at"] = now
                return True
        return False

    def _expire_resource_locks(self, now: datetime) -> None:
        for row in self._resource_locks:
            if row["status"] == "ACTIVE" and not row["deleted"] and row["lease_expires_at"] <= now:
                row["status"] = "EXPIRED"
                row["updated_at"] = now
