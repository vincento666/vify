from dataclasses import dataclass
from enum import StrEnum
from typing import Any, ClassVar, Protocol

from app.modules.runtime_lab.domain.sop import MockSopAdapter, SopTurnResult, missing_chatflow_binding_error


class SopExecutionStatus(StrEnum):
    WAITING = "WAITING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


@dataclass(frozen=True)
class SopCheckpoint:
    sop_runtime_id: str
    current_node_id: str
    current_step: str
    pending_prompt: str
    collected: dict[str, Any]
    scoped_variables: dict[str, Any]
    version: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "sopRuntimeId": self.sop_runtime_id,
            "currentNodeId": self.current_node_id,
            "currentStep": self.current_step,
            "pendingPrompt": self.pending_prompt,
            "collected": dict(self.collected),
            "scopedVariables": dict(self.scoped_variables),
            "version": self.version,
        }


@dataclass(frozen=True)
class SopExecutionRequest:
    runtime_session_id: int
    runtime_task_id: int | None
    sop_id: str
    message: str
    checkpoint: SopCheckpoint | None
    collected: dict[str, Any]
    business_refs: dict[str, Any]
    metadata: dict[str, Any]


@dataclass(frozen=True)
class SopExecutionResult:
    status: SopExecutionStatus
    current_step: str
    reply: str
    pending_prompt: str
    checkpoint: SopCheckpoint
    collected: dict[str, Any]
    business_refs: dict[str, Any]
    events: list[dict[str, Any]]
    error: dict[str, str] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "currentStep": self.current_step,
            "reply": self.reply,
            "pendingPrompt": self.pending_prompt,
            "checkpoint": self.checkpoint.to_dict(),
            "collected": dict(self.collected),
            "businessRefs": dict(self.business_refs),
            "events": [dict(event) for event in self.events],
            "error": dict(self.error) if self.error else None,
        }


class SopRuntimeAdapter(Protocol):
    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        ...

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        ...

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        ...

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        ...

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        ...


class MissingChatflowBindingAdapter:
    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return _missing_chatflow_binding_result(request)

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return _missing_chatflow_binding_result(request)

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        if request.checkpoint is not None:
            return request.checkpoint
        return _missing_chatflow_binding_checkpoint(request)

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return _missing_chatflow_binding_result(request)

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        return False


class FakeSopRuntimeAdapter:
    _runtime_results: ClassVar[dict[int, dict[str, Any]]] = {}

    def __init__(self, mock_adapter: MockSopAdapter | None = None) -> None:
        self._mock_adapter = mock_adapter or MockSopAdapter()

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        try:
            result = self._mock_adapter.start(request.sop_id, message=request.message, collected=request.collected)
        except KeyError:
            return self._failure(request)
        return self._execution_result(request, result, "SOP_STARTED")

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        current_step = request.checkpoint.current_step if request.checkpoint else "collect_order_no"
        collected = dict(request.checkpoint.collected) if request.checkpoint else dict(request.collected)
        try:
            result = self._mock_adapter.continue_task(
                sop_id=request.sop_id,
                current_step=current_step,
                message=request.message,
                collected=collected,
            )
        except KeyError:
            return self._failure(request)
        return self._execution_result(request, result, "SOP_CONTINUED")

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        if request.checkpoint is not None:
            self._remember_checkpoint(request.checkpoint)
            return request.checkpoint
        checkpoint = self._checkpoint(
            request,
            current_step="collect_order_no",
            pending_prompt="",
            collected=request.collected,
        )
        self._remember_checkpoint(checkpoint)
        return checkpoint

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        if request.checkpoint is None:
            checkpoint = self._checkpoint(
                request,
                current_step="collect_order_no",
                pending_prompt="",
                collected=request.collected,
            )
        else:
            checkpoint = request.checkpoint
        result = SopExecutionResult(
            status=SopExecutionStatus.WAITING,
            current_step=checkpoint.current_step,
            reply=f"已恢复流程。{checkpoint.pending_prompt}",
            pending_prompt=checkpoint.pending_prompt,
            checkpoint=checkpoint,
            collected=dict(checkpoint.collected),
            business_refs=dict(checkpoint.collected),
            events=[{"type": "SOP_RESUMED", "sopId": request.sop_id}],
            error=None,
        )
        self._remember_result(result)
        return result

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        return self._mock_adapter.is_interruptible(sop_id, step_id)

    def get_result(self, run_id: int) -> dict[str, Any]:
        return dict(self._runtime_results.get(int(run_id)) or {})

    def _execution_result(
        self,
        request: SopExecutionRequest,
        result: SopTurnResult,
        event_type: str,
    ) -> SopExecutionResult:
        checkpoint = self._checkpoint(
            request,
            current_step=result.current_step,
            pending_prompt=result.pending_prompt,
            collected=result.collected,
        )
        status = SopExecutionStatus.COMPLETED if result.completed else SopExecutionStatus.WAITING
        execution_result = SopExecutionResult(
            status=status,
            current_step=result.current_step,
            reply=result.reply,
            pending_prompt=result.pending_prompt,
            checkpoint=checkpoint,
            collected=dict(result.collected),
            business_refs=dict(result.collected),
            events=[{"type": event_type, "sopId": request.sop_id, "currentStep": result.current_step}],
            error=None,
        )
        self._remember_result(execution_result)
        return execution_result

    def _checkpoint(
        self,
        request: SopExecutionRequest,
        current_step: str,
        pending_prompt: str,
        collected: dict[str, Any],
    ) -> SopCheckpoint:
        scoped_variables: dict[str, Any] = {
            f"conversation.{key}": value
            for key, value in collected.items()
        }
        scoped_variables["__chatflow"] = _synthetic_chatflow_meta(
            request.sop_id, request.runtime_session_id, request.runtime_task_id
        )
        runtime_id = request.runtime_task_id if request.runtime_task_id is not None else "new"
        return SopCheckpoint(
            sop_runtime_id=f"fake:{request.sop_id}:{runtime_id}",
            current_node_id=current_step,
            current_step=current_step,
            pending_prompt=pending_prompt,
            collected=dict(collected),
            scoped_variables=scoped_variables,
            version=1,
        )

    def _failure(self, request: SopExecutionRequest) -> SopExecutionResult:
        checkpoint = self._checkpoint(request, current_step="", pending_prompt="", collected={})
        result = SopExecutionResult(
            status=SopExecutionStatus.FAILED,
            current_step="",
            reply="",
            pending_prompt="",
            checkpoint=checkpoint,
            collected={},
            business_refs={},
            events=[{"type": "SOP_FAILED", "sopId": request.sop_id}],
            error={"code": "SOP_NOT_FOUND", "message": f"Unknown SOP: {request.sop_id}"},
        )
        self._remember_result(result)
        return result

    def _remember_result(self, result: SopExecutionResult) -> None:
        self._remember_checkpoint(result.checkpoint, status=result.status.value)

    def _remember_checkpoint(self, checkpoint: SopCheckpoint, status: str = "WAITING") -> None:
        meta = checkpoint.scoped_variables.get("__chatflow")
        if not isinstance(meta, dict):
            return
        run_id = meta.get("runId")
        try:
            run_id_int = int(run_id)
        except (TypeError, ValueError):
            return
        self._runtime_results[run_id_int] = {
            "runId": run_id_int,
            "status": status,
            "checkpoint": {
                "pendingNodeKey": checkpoint.current_step,
                "pendingPrompt": checkpoint.pending_prompt,
            },
        }


def _synthetic_chatflow_meta(
    sop_id: str,
    runtime_session_id: int | None,
    runtime_task_id: int | None,
) -> dict[str, Any]:
    """Build a deterministic ``__chatflow`` meta block for fake adapters.

    Slice 213.3.5a: aggregator now reads chatflow refs from
    ``checkpoint.scoped_variables.__chatflow`` and the runtime-lab service
    writes ``task.chatflow_*`` columns from the same source (via
    :func:`_chatflow_refs_from_checkpoint`). Fake adapters used in tests
    must emit synthetic but well-formed meta so this dual-write path
    exercises the same branches as :class:`ChatflowSopRuntimeAdapter`.

    The synthetic ids are derived from ``sop_id`` and the runtime session /
    task ids so the same fake turn always produces the same refs.
    """
    chatflow_id = abs(hash(("chatflow_id", sop_id))) % 100000 or 1
    session_seed = runtime_session_id if runtime_session_id is not None else 0
    task_seed = runtime_task_id if runtime_task_id is not None else 0
    session_id = abs(hash(("session_id", sop_id, session_seed))) % 100000 or 1
    run_id = abs(hash(("run_id", sop_id, session_seed, task_seed))) % 100000 or 1
    return {
        "chatflowId": chatflow_id,
        "sessionId": session_id,
        "runId": run_id,
        "eventId": 0,
        "checkpointId": 0,
        "runtimeVersion": "v2",
        "runtimeRefs": {
            "runId": run_id,
            "statusRef": f"/api/v1/runtime-runs/{run_id}",
            "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
            "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
            "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
            "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
        },
        "runtimeStatus": "RUNNING",
        "fallbackReason": None,
    }


def _missing_chatflow_binding_result(request: SopExecutionRequest) -> SopExecutionResult:
    error = missing_chatflow_binding_error(request.sop_id)
    return SopExecutionResult(
        status=SopExecutionStatus.FAILED,
        current_step="",
        reply="",
        pending_prompt="",
        checkpoint=_missing_chatflow_binding_checkpoint(request),
        collected={},
        business_refs={},
        events=[{"type": "MISSING_CHATFLOW_BINDING", "sopId": request.sop_id}],
        error=error,
    )


def _missing_chatflow_binding_checkpoint(request: SopExecutionRequest) -> SopCheckpoint:
    runtime_id = request.runtime_task_id if request.runtime_task_id is not None else "new"
    return SopCheckpoint(
        sop_runtime_id=f"missing-chatflow-binding:{request.sop_id}:{runtime_id}",
        current_node_id="",
        current_step="",
        pending_prompt="",
        collected={},
        scoped_variables={},
        version=1,
    )
