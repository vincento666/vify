from dataclasses import dataclass
from enum import StrEnum
from typing import Any, Protocol

from app.modules.runtime_lab.domain.sop import MockSopAdapter, SopTurnResult


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


class FakeSopRuntimeAdapter:
    def __init__(self, mock_adapter: MockSopAdapter | None = None) -> None:
        self._mock_adapter = mock_adapter or MockSopAdapter()

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        try:
            result = self._mock_adapter.start(request.sop_id, message=request.message)
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
            return request.checkpoint
        return self._checkpoint(
            request,
            current_step="collect_order_no",
            pending_prompt="",
            collected=request.collected,
        )

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
        return SopExecutionResult(
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

    def is_interruptible(self, sop_id: str, step_id: str) -> bool:
        return self._mock_adapter.is_interruptible(sop_id, step_id)

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
        return SopExecutionResult(
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

    def _checkpoint(
        self,
        request: SopExecutionRequest,
        current_step: str,
        pending_prompt: str,
        collected: dict[str, Any],
    ) -> SopCheckpoint:
        scoped_variables = {
            f"conversation.{key}": value
            for key, value in collected.items()
        }
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
        return SopExecutionResult(
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
