from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any
from uuid import uuid4


TERMINAL_RUN_STATUSES = {"COMPLETED", "FAILED", "DENIED", "CANCELLED", "WAITING_APPROVAL"}
RUNNABLE_STATUSES = {"QUEUED", "RUNNING"}


class RunControlConflict(RuntimeError):
    pass


def build_run_checkpoint(
    *,
    run_id: int,
    status: str,
    phase: str,
    last_sequence: int,
    request: dict[str, Any] | None = None,
    worker: dict[str, Any] | None = None,
    control: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "runId": run_id,
        "status": status,
        "phase": phase,
        "streamCursor": {"lastSequence": max(0, int(last_sequence))},
        "request": request or {},
        "checkpointAt": datetime.now().isoformat(),
    }
    if worker:
        payload["worker"] = worker
    if control:
        payload["control"] = control
    return payload


def apply_control_transition(runtime_state: dict[str, Any], *, action: str, actor_id: str) -> dict[str, Any]:
    current_status = str(runtime_state.get("status") or "")
    if action == "pause":
        next_status = "PAUSED" if current_status not in TERMINAL_RUN_STATUSES else current_status
    elif action == "resume":
        next_status = "QUEUED" if current_status == "PAUSED" else current_status
    elif action == "cancel":
        next_status = "CANCELLED" if current_status not in {"COMPLETED", "FAILED", "DENIED"} else current_status
    else:
        raise ValueError(f"Unsupported run control action: {action}")
    return {
        **runtime_state,
        "status": next_status,
        "control": {
            "action": action,
            "actorId": actor_id,
            "previousStatus": current_status,
            "status": next_status,
            "decidedAt": datetime.now().isoformat(),
        },
    }


def worker_claim_payload(*, worker_id: str | None = None, lease_seconds: int = 30) -> dict[str, Any]:
    claimed_at = datetime.now()
    resolved_worker_id = worker_id or f"ai-assistant-worker-{uuid4().hex}"
    lease_token = uuid4().hex
    return {
        "workerId": resolved_worker_id,
        "claimedAt": claimed_at.isoformat(),
        "leaseToken": lease_token,
        "leaseExpiresAt": (claimed_at + timedelta(seconds=max(1, int(lease_seconds)))).isoformat(),
        "scope": "durable-lease",
    }


def runtime_payload_from_run(run: dict[str, Any]) -> dict[str, Any]:
    input_payload = run.get("input_payload") or {}
    runtime = input_payload.get("sessionRuntime") if isinstance(input_payload, dict) else None
    return dict(runtime) if isinstance(runtime, dict) else {}


def request_payload_from_run(run: dict[str, Any]) -> dict[str, Any]:
    runtime = runtime_payload_from_run(run)
    request = runtime.get("request")
    return dict(request) if isinstance(request, dict) else {}
