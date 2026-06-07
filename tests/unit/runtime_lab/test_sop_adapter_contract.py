import unittest

from app.modules.runtime_lab.domain.sop_adapter import (
    FakeSopRuntimeAdapter,
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionStatus,
)


class SopAdapterContractTest(unittest.TestCase):
    def test_start_returns_waiting_result_with_serializable_checkpoint(self) -> None:
        adapter = FakeSopRuntimeAdapter()

        result = adapter.start_sop(_request(sop_id="refund_ticket", message="我要退票"))

        self.assertEqual(result.status, SopExecutionStatus.WAITING)
        self.assertEqual(result.current_step, "collect_order_no")
        self.assertIn("订单号", result.reply)
        self.assertEqual(result.checkpoint.current_step, "collect_order_no")
        self.assertEqual(result.checkpoint.pending_prompt, "请提供订单号。")
        self.assertEqual(result.to_dict()["checkpoint"]["currentStep"], "collect_order_no")

    def test_continue_updates_collected_values_and_completion_status(self) -> None:
        adapter = FakeSopRuntimeAdapter()
        started = adapter.start_sop(_request(sop_id="refund_ticket", message="我要退票"))

        collected = adapter.continue_sop(
            _request(
                sop_id="refund_ticket",
                message="TK-100",
                checkpoint=started.checkpoint,
                collected=started.collected,
            )
        )
        completed = adapter.continue_sop(
            _request(
                sop_id="refund_ticket",
                message="确认",
                checkpoint=collected.checkpoint,
                collected=collected.collected,
            )
        )

        self.assertEqual(collected.status, SopExecutionStatus.WAITING)
        self.assertEqual(collected.current_step, "confirm")
        self.assertEqual(collected.collected["order_no"], "TK-100")
        self.assertEqual(completed.status, SopExecutionStatus.COMPLETED)
        self.assertEqual(completed.current_step, "completed")

    def test_suspend_and_resume_round_trip_checkpoint_without_task_ledger_mutation(self) -> None:
        adapter = FakeSopRuntimeAdapter()
        checkpoint = SopCheckpoint(
            sop_runtime_id="fake:refund_ticket:42",
            current_node_id="confirm",
            current_step="confirm",
            pending_prompt="请回复 confirm 或 确认 完成办理。",
            collected={"order_no": "TK-100"},
            scoped_variables={"conversation.order_no": "TK-100"},
            version=1,
        )

        suspended = adapter.suspend_sop(_request(sop_id="refund_ticket", checkpoint=checkpoint))
        resumed = adapter.resume_sop(_request(sop_id="refund_ticket", checkpoint=suspended))

        self.assertEqual(suspended.to_dict()["scopedVariables"]["conversation.order_no"], "TK-100")
        self.assertEqual(resumed.status, SopExecutionStatus.WAITING)
        self.assertEqual(resumed.current_step, "confirm")
        self.assertEqual(resumed.collected["order_no"], "TK-100")
        self.assertFalse(any(event.get("type") == "TASK_MUTATED" for event in resumed.events))

    def test_unknown_sop_returns_normalized_failure(self) -> None:
        adapter = FakeSopRuntimeAdapter()

        result = adapter.start_sop(_request(sop_id="missing_sop"))

        self.assertEqual(result.status, SopExecutionStatus.FAILED)
        self.assertEqual(result.error, {"code": "SOP_NOT_FOUND", "message": "Unknown SOP: missing_sop"})
        self.assertEqual(result.to_dict()["error"]["code"], "SOP_NOT_FOUND")


def _request(
    sop_id: str,
    message: str = "",
    checkpoint: SopCheckpoint | None = None,
    collected: dict[str, object] | None = None,
) -> SopExecutionRequest:
    return SopExecutionRequest(
        runtime_session_id=7,
        runtime_task_id=42,
        sop_id=sop_id,
        message=message,
        checkpoint=checkpoint,
        collected=collected or {},
        business_refs={},
        metadata={"source": "unit"},
    )
