from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


ACTIVE_STATUSES = {"QUEUED", "RUNNING"}


@dataclass(frozen=True)
class RuntimeConcurrencyLimits:
    tenant_active_limit: int = 0
    workflow_active_limit: int = 0
    chatflow_active_limit: int = 0
    worker_running_limit: int = 0
    provider_active_limit: int = 0
    queue_capacity_limit: int = 0


@dataclass(frozen=True)
class RuntimeQueueSnapshot:
    tenant_active: int = 0
    owner_active: int = 0
    worker_running: int = 0
    provider_active: int = 0
    queued_total: int = 0


@dataclass(frozen=True)
class RuntimeQueueDecision:
    status: str
    admitted: bool
    level: str
    current: int = 0
    limit: int = 0
    reason: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "admitted": self.admitted,
            "level": self.level,
            "current": self.current,
            "limit": self.limit,
            "reason": self.reason,
        }


class RuntimeConcurrencyGate:
    def __init__(self, limits: RuntimeConcurrencyLimits) -> None:
        self._limits = limits

    def snapshot(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        owner_type: str,
        owner_id: int,
        tenant_id: str,
        provider_keys: Iterable[str],
        worker_id: str = "",
    ) -> RuntimeQueueSnapshot:
        normalized_owner_type = str(owner_type or "").upper()
        normalized_tenant_id = str(tenant_id or "local")
        normalized_provider_keys = {str(item) for item in provider_keys if str(item)}
        normalized_worker_id = str(worker_id or "")
        tenant_active = 0
        owner_active = 0
        worker_running = 0
        provider_active = 0
        queued_total = 0
        for row in rows:
            status = str(row.get("status") or "").upper()
            if status not in ACTIVE_STATUSES:
                continue
            payload = _payload(row)
            if status == "QUEUED":
                queued_total += 1
            if str(payload.get("tenantId") or "local") == normalized_tenant_id:
                tenant_active += 1
            if str(row.get("owner_type") or "").upper() == normalized_owner_type and int(row.get("owner_id") or 0) == int(owner_id):
                owner_active += 1
            if normalized_worker_id and status == "RUNNING" and str(row.get("lease_owner") or "") == normalized_worker_id:
                worker_running += 1
            if normalized_provider_keys and normalized_provider_keys.intersection(_provider_keys(payload)):
                provider_active += 1
        return RuntimeQueueSnapshot(
            tenant_active=tenant_active,
            owner_active=owner_active,
            worker_running=worker_running,
            provider_active=provider_active,
            queued_total=queued_total,
        )

    def decide(
        self,
        rows: Iterable[Mapping[str, Any]],
        *,
        owner_type: str,
        owner_id: int,
        tenant_id: str,
        provider_keys: Iterable[str],
        worker_id: str = "",
    ) -> RuntimeQueueDecision:
        snapshot = self.snapshot(
            rows,
            owner_type=owner_type,
            owner_id=owner_id,
            tenant_id=tenant_id,
            provider_keys=provider_keys,
            worker_id=worker_id,
        )
        if _limit_reached(snapshot.tenant_active, self._limits.tenant_active_limit):
            return _decision("rate_limited", False, "tenant", snapshot.tenant_active, self._limits.tenant_active_limit)
        if _limit_reached(snapshot.queued_total, self._limits.queue_capacity_limit):
            return _decision("rejected", False, "queue", snapshot.queued_total, self._limits.queue_capacity_limit)
        owner_limit = (
            self._limits.chatflow_active_limit
            if str(owner_type or "").upper() == "CHATFLOW"
            else self._limits.workflow_active_limit
        )
        owner_level = "chatflow" if str(owner_type or "").upper() == "CHATFLOW" else "workflow"
        if _limit_reached(snapshot.owner_active, owner_limit):
            return _decision("queued", True, owner_level, snapshot.owner_active, owner_limit)
        if _limit_reached(snapshot.worker_running, self._limits.worker_running_limit):
            return _decision("queued", True, "worker", snapshot.worker_running, self._limits.worker_running_limit)
        if _limit_reached(snapshot.provider_active, self._limits.provider_active_limit):
            return _decision("degraded", False, "provider", snapshot.provider_active, self._limits.provider_active_limit)
        return RuntimeQueueDecision(status="queued", admitted=True, level="none", reason="within_limits")


def _decision(status: str, admitted: bool, level: str, current: int, limit: int) -> RuntimeQueueDecision:
    return RuntimeQueueDecision(
        status=status,
        admitted=admitted,
        level=level,
        current=current,
        limit=limit,
        reason=f"{level}_limit_reached",
    )


def _limit_reached(current: int, limit: int) -> bool:
    return int(limit or 0) > 0 and current >= int(limit)


def _payload(row: Mapping[str, Any]) -> Mapping[str, Any]:
    payload = row.get("payload")
    return payload if isinstance(payload, Mapping) else {}


def _provider_keys(payload: Mapping[str, Any]) -> set[str]:
    raw = payload.get("providerKeys") or payload.get("provider_keys") or []
    if isinstance(raw, str):
        return {raw} if raw else set()
    if isinstance(raw, Iterable):
        return {str(item) for item in raw if str(item)}
    return set()
