from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import posixpath
from typing import Any, Protocol


class ResourceLockMode(StrEnum):
    READ = "READ"
    WRITE = "WRITE"


@dataclass(frozen=True)
class ResourceLockAcquireResult:
    status: str
    resource_key: str
    mode: ResourceLockMode
    owner_session_id: int
    owner_run_id: int
    lease_expires_at: str | None
    fencing_token: int
    observation: dict[str, Any]
    events: list[dict[str, Any]]


class ResourceLockRepository(Protocol):
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
        ...

    def release_resource_lock(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
    ) -> bool:
        ...

    def renew_resource_lock(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
        ttl_seconds: int,
    ) -> bool:
        ...


class ResourceLockManager:
    def __init__(self, repository: ResourceLockRepository) -> None:
        self._repository = repository

    def acquire(
        self,
        *,
        resource_key: str,
        mode: ResourceLockMode,
        owner_session_id: int,
        owner_run_id: int,
        ttl_seconds: int = 30,
        owner_tool_call_id: int | None = None,
    ) -> ResourceLockAcquireResult:
        resource_key = _canonical_resource_key(resource_key)
        requested = _event(
            "resource_lock.acquire_requested",
            resource_key=resource_key,
            mode=mode.value,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
        )
        row = self._repository.acquire_resource_lock(
            resource_key=resource_key,
            mode=mode.value,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
            owner_tool_call_id=owner_tool_call_id,
            ttl_seconds=ttl_seconds,
        )
        status = str(row.get("status") or "CONTENDED")
        fencing_token = int(row.get("fencing_token") or 0)
        lease_expires_at = row.get("lease_expires_at")
        if status == "ACQUIRED":
            acquired = _event(
                "resource_lock.acquired",
                resource_key=resource_key,
                mode=mode.value,
                owner_session_id=owner_session_id,
                owner_run_id=owner_run_id,
                extra={
                    "leaseExpiresAt": str(lease_expires_at) if lease_expires_at is not None else None,
                    "fencingToken": fencing_token,
                },
            )
            return ResourceLockAcquireResult(
                status="ACQUIRED",
                resource_key=resource_key,
                mode=mode,
                owner_session_id=owner_session_id,
                owner_run_id=owner_run_id,
                lease_expires_at=str(lease_expires_at) if lease_expires_at is not None else None,
                fencing_token=fencing_token,
                observation={},
                events=[requested, acquired],
            )
        observation = _contention_observation(
            resource_key=resource_key,
            mode=mode,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
            reason=str(row.get("reason") or "resource lock is contended"),
        )
        contended = _event(
            "resource_lock.contended",
            resource_key=resource_key,
            mode=mode.value,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
            extra={"reason": observation["error"]["message"], "requestedMode": mode.value},
        )
        return ResourceLockAcquireResult(
            status="CONTENDED",
            resource_key=resource_key,
            mode=mode,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
            lease_expires_at=None,
            fencing_token=0,
            observation=observation,
            events=[requested, contended],
        )

    def release(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
    ) -> bool:
        resource_key = _canonical_resource_key(resource_key)
        return self._repository.release_resource_lock(
            resource_key=resource_key,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
            fencing_token=fencing_token,
        )

    def renew(
        self,
        *,
        resource_key: str,
        owner_session_id: int,
        owner_run_id: int,
        fencing_token: int,
        ttl_seconds: int,
    ) -> bool:
        resource_key = _canonical_resource_key(resource_key)
        return self._repository.renew_resource_lock(
            resource_key=resource_key,
            owner_session_id=owner_session_id,
            owner_run_id=owner_run_id,
            fencing_token=fencing_token,
            ttl_seconds=ttl_seconds,
        )


def release_event(
    *,
    resource_key: str,
    mode: ResourceLockMode,
    owner_session_id: int,
    owner_run_id: int,
    fencing_token: int,
) -> dict[str, Any]:
    resource_key = _canonical_resource_key(resource_key)
    return _event(
        "resource_lock.released",
        resource_key=resource_key,
        mode=mode.value,
        owner_session_id=owner_session_id,
        owner_run_id=owner_run_id,
        extra={"fencingToken": fencing_token},
    )


def _event(
    event_type: str,
    *,
    resource_key: str,
    mode: str,
    owner_session_id: int,
    owner_run_id: int,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload = {
        "sessionId": owner_session_id,
        "runId": owner_run_id,
        "resourceKey": resource_key,
        "mode": mode,
        "ownerSessionId": owner_session_id,
        "ownerRunId": owner_run_id,
    }
    if event_type == "resource_lock.contended":
        payload.pop("mode", None)
    if extra:
        payload.update(extra)
    return {"type": event_type, "payload": payload}


def _canonical_resource_key(resource_key: str) -> str:
    key = str(resource_key or "")
    if not key.startswith("file:"):
        return key
    raw_path = key.removeprefix("file:").replace("\\", "/")
    normalized = posixpath.normpath(raw_path)
    if normalized == ".":
        normalized = ""
    while normalized.startswith("./"):
        normalized = normalized[2:]
    return f"file:{normalized}"


def _contention_observation(
    *,
    resource_key: str,
    mode: ResourceLockMode,
    owner_session_id: int,
    owner_run_id: int,
    reason: str,
) -> dict[str, Any]:
    return {
        "kind": "tool_error",
        "toolName": "resource_lock",
        "toolInput": {"resourceKey": resource_key, "mode": mode.value},
        "attempts": 0,
        "error": {
            "code": "RESOURCE_LOCK_CONTENDED",
            "message": reason,
            "type": "resource_lock_contended",
            "retriable": True,
        },
        "retriable": True,
        "modelVisible": True,
        "owner": {"sessionId": owner_session_id, "runId": owner_run_id},
        "suggestedActions": ["retry_later", "revise_plan", "choose_alternative_resource"],
    }
