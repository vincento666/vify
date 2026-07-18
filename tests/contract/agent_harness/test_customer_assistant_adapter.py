from app.modules.agent_harness import (
    HarnessEvent,
    HarnessRunResult,
    HarnessRunStatus,
)
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus
from app.modules.customer_assistant.domain.react_worker import (
    FakeReactWorkerModel,
    ReactModelAction,
    RestrictedReactWorker,
)
from app.modules.customer_assistant.domain.worker_registry import ReactWorkerConfig


class RecordingAgentHarness:
    def __init__(self) -> None:
        self.request = None
        self.profile = None

    def execute(self, request, profile):
        self.request = request
        self.profile = profile
        return HarnessRunResult(
            status=HarnessRunStatus.COMPLETED,
            output={
                "operatorRecommendation": "Order is refundable.",
                "customerReplyDraft": "订单可以退票。",
            },
            observations=(),
            events=(
                HarnessEvent(type="harness.started"),
                HarnessEvent(type="harness.iteration.started", iteration=1),
                HarnessEvent(type="harness.completed", iteration=1),
            ),
        )


def test_customer_assistant_worker_runs_through_agent_harness_interface() -> None:
    harness = RecordingAgentHarness()
    worker = RestrictedReactWorker(
        config=ReactWorkerConfig(
            worker_ref="refund_status_react",
            task_type="refund_status",
            allowed_tools=("lookup_order",),
            max_iterations=3,
            timeout_ms=1000,
        ),
        model=FakeReactWorkerModel(
            [
                ReactModelAction.final(
                    operator_recommendation="unused",
                    customer_reply_draft="unused",
                )
            ]
        ),
        tools={},
        harness=harness,
    )

    result = worker.run(_task(), "查 TK-100 退票状态")

    assert harness.request.run_id == "refund_status:TK-100"
    assert harness.request.max_iterations == 3
    assert harness.profile is not None
    assert result.status is TaskStatus.COMPLETED
    assert result.customer_reply_draft == "订单可以退票。"


def _task() -> TaskItem:
    return TaskItem(
        id=77,
        session_id=12,
        task_key="refund_status:TK-100",
        task_type="refund_status",
        business_key="TK-100",
        short_id="REF77",
        status=TaskStatus.PENDING,
        worker_type="react_worker",
        worker_ref="refund_status_react",
    )
