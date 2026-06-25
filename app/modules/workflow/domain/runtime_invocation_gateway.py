from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol


class RuntimeV2InvocationService(Protocol):
    def start_run(
        self,
        owner_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        ...

    def complete_run(self, run_id: int) -> None:
        ...

    def resume_run(
        self,
        run_id: int,
        resume_data: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        ...

    def get_result(self, run_id: int) -> dict[str, Any]:
        ...

    def list_events(self, run_id: int, after_sequence: int = 0) -> dict[str, Any]:
        ...


class RuntimeInvocationGateway:
    def __init__(
        self,
        service: RuntimeV2InvocationService,
        *,
        enqueue_background_run: Callable[[int, int], dict[str, Any] | None] | None = None,
    ) -> None:
        self._service = service
        self._enqueue_background_run = enqueue_background_run

    def start_only(
        self,
        *,
        owner_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        started = self._service.start_run(owner_id, dict(input_data), idempotency_key, version_id)
        return _unified_invocation(
            started,
            result=None,
            events={"list": [], "total": 0},
        )

    def start_and_wait(
        self,
        *,
        owner_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        started = self.start_only(
            owner_id=owner_id,
            input_data=input_data,
            idempotency_key=idempotency_key,
            version_id=version_id,
        )
        run_id = int(started["runId"])
        if not bool(started.get("idempotentReplay")):
            self._service.complete_run(run_id)
        return _unified_invocation(
            started,
            result=self._service.get_result(run_id),
            events=self._service.list_events(run_id),
        )

    def start_and_stream_ref(
        self,
        *,
        owner_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        started = self.start_only(
            owner_id=owner_id,
            input_data=input_data,
            idempotency_key=idempotency_key,
            version_id=version_id,
        )
        started["streamRef"] = started["runtimeRefs"]["eventStreamRef"]
        if self._enqueue_background_run is not None:
            job = self._enqueue_background_run(owner_id, int(started["runId"]))
            if job is not None:
                started["backgroundJob"] = job
        return started

    def resume_and_wait(
        self,
        *,
        run_id: int,
        resume_data: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        result = self._service.resume_run(run_id, dict(resume_data), idempotency_key)
        return _unified_invocation(
            {"runId": run_id, **_refs_from(result)},
            result=result,
            events=self._service.list_events(run_id),
        )

    # Compatibility aliases for callers that mirror external API naming.
    startOnly = start_only
    startAndWait = start_and_wait
    startAndStreamRef = start_and_stream_ref
    resumeAndWait = resume_and_wait


def _unified_invocation(
    data: dict[str, Any],
    *,
    result: dict[str, Any] | None,
    events: dict[str, Any],
) -> dict[str, Any]:
    refs = _refs_from(data)
    run_id = int(data["runId"])
    status = str((result or data).get("status") or "RUNNING")
    unified = dict(data)
    unified.update(refs)
    unified["runId"] = run_id
    unified["status"] = status
    unified["runtimeVersion"] = 2
    unified["runtimeRefs"] = {"runId": run_id, **refs}
    unified["result"] = result
    unified["events"] = events
    return unified


def _refs_from(data: dict[str, Any]) -> dict[str, Any]:
    run_id = int(data["runId"])
    return {
        "statusRef": str(data.get("statusRef") or f"/api/v1/runtime-runs/{run_id}"),
        "eventsRef": str(data.get("eventsRef") or f"/api/v1/runtime-runs/{run_id}/events"),
        "eventStreamRef": str(
            data.get("eventStreamRef")
            or f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0"
        ),
        "nodesRef": str(data.get("nodesRef") or f"/api/v1/runtime-runs/{run_id}/nodes"),
        "resultRef": str(data.get("resultRef") or f"/api/v1/runtime-runs/{run_id}/result"),
    }
