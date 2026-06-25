import unittest
from typing import Any

from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.sop_adapter import SopExecutionRequest, SopExecutionStatus


class ChatflowSopRuntimeAdapterGatewayTest(unittest.TestCase):
    def test_start_sop_v2_uses_runtime_invocation_gateway_start_and_wait(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
        )

        result = adapter.start_sop(_request(message="我要退票"))

        self.assertEqual(gateway.calls[0][0], "start_and_wait")
        self.assertEqual(gateway.calls[0][1], 42)
        self.assertEqual(gateway.calls[0][2]["sys.query"], "我要退票")
        self.assertEqual(result.status, SopExecutionStatus.WAITING)
        self.assertEqual(result.current_step, "info_order")
        meta = result.checkpoint.scoped_variables["__chatflow"]
        self.assertEqual(meta["runtimeVersion"], 2)
        self.assertEqual(meta["runtimeRefs"]["eventStreamRef"], "/api/v1/runtime-runs/501/events/stream?afterSequence=0")

    def test_continue_sop_v2_uses_runtime_invocation_gateway_resume_and_wait(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
        )

        started = adapter.start_sop(_request(message="我要退票"))
        continued = adapter.continue_sop(_request(message="手机号 13800138000", checkpoint=started.checkpoint))

        self.assertEqual(gateway.calls[-1][0], "resume_and_wait")
        self.assertEqual(gateway.calls[-1][1], 501)
        self.assertEqual(gateway.calls[-1][2]["collected"]["phone"], "13800138000")
        self.assertEqual(continued.status, SopExecutionStatus.COMPLETED)
        self.assertEqual(continued.current_step, "completed")
        self.assertEqual(continued.collected["phone"], "13800138000")

    def test_start_sop_async_mode_returns_runtime_refs_without_waiting_for_completion(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
            runtime_invocation_mode="async",
        )

        result = adapter.start_sop(_request(message="我要退票"))

        self.assertEqual(gateway.calls, [("start_and_stream_ref", 42, "我要退票")])
        self.assertEqual(result.status, SopExecutionStatus.WAITING)
        self.assertEqual(result.current_step, "runtime_running")
        meta = result.checkpoint.scoped_variables["__chatflow"]
        self.assertEqual(meta["runtimeVersion"], 2)
        self.assertEqual(meta["resumeMode"], "runtime-ref")
        self.assertEqual(meta["runtimeStatus"], "RUNNING")
        self.assertEqual(meta["runtimeRefs"]["eventStreamRef"], "/api/v1/runtime-runs/501/events/stream?afterSequence=0")
        self.assertIn("chatflow_v2_async_started", [event["type"] for event in result.events])


class _FakeRuntimeInvocationGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []

    def start_and_wait(
        self,
        *,
        owner_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("start_and_wait", owner_id, input_data, idempotency_key, version_id))
        return _invocation(
            status="INTERRUPTED",
            output={
                "interrupt": {
                    "nodeKey": "info_order",
                    "question": "请提供订单号和手机号。",
                },
                "collected": {},
            },
            events=[
                {
                    "id": 1,
                    "sequence": 1,
                    "type": "workflow_node_waiting",
                    "runId": 501,
                    "checkpointId": 9001,
                    "payload": {
                        "nodeType": "INFORMATION_COLLECTION",
                        "callerContext": {"sop_key": "refund_ticket"},
                    },
                    "observability": {
                        "correlationRefs": {"nodeKey": "info_order"},
                    },
                }
            ],
        )

    def start_and_stream_ref(
        self,
        *,
        owner_id: int,
        input_data: dict[str, Any],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("start_and_stream_ref", owner_id, input_data["sys.query"]))
        refs = _runtime_refs()
        return {
            "runId": 501,
            "sessionId": "session-501",
            "status": "RUNNING",
            "runtimeVersion": 2,
            "runtimeRefs": refs,
            "streamRef": refs["eventStreamRef"],
            "events": {"list": [], "total": 0},
            "result": None,
        }

    def resume_and_wait(
        self,
        *,
        run_id: int,
        resume_data: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("resume_and_wait", run_id, resume_data, idempotency_key))
        return _invocation(
            status="SUCCEEDED",
            output={"final": "phone=13800138000", "collected": {"phone": "13800138000"}},
            events=[
                {
                    "id": 2,
                    "sequence": 2,
                    "type": "workflow_run_completed",
                    "runId": run_id,
                    "payload": {"status": "SUCCEEDED"},
                    "observability": {},
                }
            ],
        )


class _FakeWorkflowService:
    def execute(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("legacy workflow execute should not be used for gateway-backed v2 SOP")

    def resume_run(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("legacy workflow resume should not be used for gateway-backed v2 SOP")

    def get_session_state(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return {"variables": {}}


def _request(
    *,
    message: str,
    checkpoint: Any | None = None,
) -> SopExecutionRequest:
    return SopExecutionRequest(
        runtime_session_id=1001,
        runtime_task_id=2002,
        sop_id="refund_ticket",
        message=message,
        checkpoint=checkpoint,
        collected={},
        business_refs={},
        metadata={
            "conversationId": "gateway-sop-test",
            "userId": "operator",
            "channel": "runtime-lab",
        },
    )


def _invocation(
    *,
    status: str,
    output: dict[str, Any],
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    refs = _runtime_refs()
    return {
        "runId": 501,
        "sessionId": "session-501",
        "status": status,
        "runtimeVersion": 2,
        "runtimeRefs": dict(refs),
        "result": {
            "runId": 501,
            "status": status,
            "output": output,
            "checkpoint": {"id": 9001},
        },
        "events": {"list": events, "total": len(events)},
    }


def _runtime_refs() -> dict[str, Any]:
    return {
        "runId": 501,
        "statusRef": "/api/v1/runtime-runs/501",
        "eventsRef": "/api/v1/runtime-runs/501/events",
        "eventStreamRef": "/api/v1/runtime-runs/501/events/stream?afterSequence=0",
        "nodesRef": "/api/v1/runtime-runs/501/nodes",
        "resultRef": "/api/v1/runtime-runs/501/result",
    }


if __name__ == "__main__":
    unittest.main()
