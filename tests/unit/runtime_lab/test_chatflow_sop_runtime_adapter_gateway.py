import unittest
import hashlib
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter, _v2_idempotency_key
from app.modules.runtime_lab.domain.sop_adapter import SopExecutionRequest, SopExecutionStatus


class ChatflowSopRuntimeAdapterGatewayTest(unittest.TestCase):
    def test_v2_idempotency_key_uses_process_stable_message_digest(self) -> None:
        request = _request(message="手机号 13800138000")

        key = _v2_idempotency_key(request)

        self.assertTrue(key.endswith(hashlib.sha256(request.message.encode("utf-8")).hexdigest()))

    def test_start_sop_v2_defaults_to_runtime_invocation_gateway_stream_ref(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
        )

        result = adapter.start_sop(_request(message="我要退票"))

        self.assertEqual(gateway.calls[0][0], "start_and_stream_ref")
        self.assertEqual(gateway.calls[0][1], 42)
        self.assertEqual(gateway.calls[0][2], "我要退票")
        self.assertEqual(result.status, SopExecutionStatus.WAITING)
        self.assertEqual(result.current_step, "runtime_running")
        meta = result.checkpoint.scoped_variables["__chatflow"]
        self.assertEqual(meta["runtimeVersion"], 2)
        self.assertEqual(meta["resumeMode"], "runtime-ref")
        self.assertEqual(meta["runtimeStatus"], "RUNNING")
        self.assertEqual(meta["runtimeRefs"]["eventStreamRef"], "/api/v1/runtime-runs/501/events/stream?afterSequence=0")

    def test_continue_sop_v2_queues_runtime_invocation_gateway_resume_without_waiting(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
        )

        started = adapter.start_sop(_request(message="我要退票"))
        continued = adapter.continue_sop(_request(message="手机号 13800138000", checkpoint=started.checkpoint))

        self.assertEqual(gateway.calls[-1][0], "resume_and_stream_ref")
        self.assertEqual(gateway.calls[-1][1], 501)
        self.assertEqual(gateway.calls[-1][2]["collected"]["phone"], "13800138000")
        self.assertEqual(continued.status, SopExecutionStatus.WAITING)
        self.assertEqual(continued.current_step, "runtime_running")
        self.assertEqual(continued.collected["phone"], "13800138000")

    def test_continue_sop_accepts_string_v2_runtime_version_from_task_refs(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
        )

        started = adapter.start_sop(_request(message="我要退票"))
        started.checkpoint.scoped_variables["__chatflow"]["runtimeVersion"] = "v2"
        continued = adapter.continue_sop(_request(message="手机号 13800138000", checkpoint=started.checkpoint))

        self.assertEqual(gateway.calls[-1][0], "resume_and_stream_ref")
        self.assertEqual(gateway.calls[-1][1], 501)
        self.assertEqual(continued.status, SopExecutionStatus.WAITING)

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

    def test_continue_sop_v2_resume_error_returns_retry_envelope_with_existing_refs(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        gateway.resume_error = BizError(ErrorCode.BAD_REQUEST, "LLM provider request failed")
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_invocation_gateway=gateway,
            runtime_invocation_mode="async",
        )

        started = adapter.start_sop(_request(message="我要退票"))
        continued = adapter.continue_sop(_request(message="订单号 CA123456，手机号 13800138000", checkpoint=started.checkpoint))

        self.assertNotEqual(continued.status, SopExecutionStatus.FAILED)
        self.assertEqual(continued.status, SopExecutionStatus.WAITING)
        meta = continued.checkpoint.scoped_variables["__chatflow"]
        self.assertEqual(meta["runtimeVersion"], 2)
        self.assertEqual(meta["runId"], 501)
        self.assertEqual(meta["runtimeRefs"]["resultRef"], "/api/v1/runtime-runs/501/result")
        self.assertIn("chatflow_v2_retryable", [event["type"] for event in continued.events])

    def test_continue_sop_v2_default_async_returns_waiting_result_after_resume(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        gateway.resume_invocation = _invocation(
            status="INTERRUPTED",
            output={
                "interrupt": {"nodeKey": "collect", "question": "还差订单号、手机号、乘机人姓名。"},
                "collected": {},
            },
            events=[
                {
                    "id": 3,
                    "sequence": 3,
                    "type": "workflow_run_interrupted",
                    "runId": 501,
                    "checkpointId": 9001,
                    "payload": {},
                    "observability": {"correlationRefs": {"nodeKey": "collect"}},
                }
            ],
        )
        runtime_v2_service = _FakeRuntimeV2Service(
            [
                _runtime_result(
                    status="INTERRUPTED",
                    output={
                        "interrupt": {"nodeKey": "collect", "question": "请提供订单号和手机号。"},
                        "collected": {},
                    },
                    checkpoint_id=9001,
                    events=[],
                ),
                _runtime_result(
                    status="SUCCEEDED",
                    output={
                        "final": "refund complete phone=13800138000 order=CA123456",
                        "collected": {"phone": "13800138000", "order_no": "CA123456"},
                    },
                    checkpoint_id=9002,
                    events=[
                        {
                            "id": 4,
                            "sequence": 4,
                            "type": "workflow_run_completed",
                            "runId": 501,
                            "payload": {"status": "SUCCEEDED"},
                            "observability": {},
                        }
                    ],
                ),
            ]
        )
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"refund_ticket": 42},
            runtime_v2_service=runtime_v2_service,
            runtime_invocation_gateway=gateway,
        )

        started = adapter.start_sop(_request(message="我要退票"))
        continued = adapter.continue_sop(_request(message="订单号 CA123456，手机号 13800138000", checkpoint=started.checkpoint))

        self.assertEqual(continued.status, SopExecutionStatus.WAITING)
        self.assertEqual(continued.current_step, "runtime_running")
        self.assertEqual(continued.collected["phone"], "13800138000")
        self.assertEqual(continued.collected["order_no"], "CA123456")
        meta = continued.checkpoint.scoped_variables["__chatflow"]
        self.assertEqual(meta["runtimeVersion"], 2)
        self.assertEqual(meta["runtimeRefs"]["resultRef"], "/api/v1/runtime-runs/501/result")

    def test_continue_sop_v2_default_async_preserves_waiting_checkpoint_for_scale_result(self) -> None:
        gateway = _FakeRuntimeInvocationGateway()
        gateway.resume_invocation = _invocation(
            status="INTERRUPTED",
            output={
                "interrupt": {"nodeKey": "confirm", "question": "请确认团队询价。"},
                "collected": {"route": "上海到广州", "travel_time": "下周三上午", "passenger_count": "十六"},
            },
            events=[
                {
                    "id": 3,
                    "sequence": 3,
                    "type": "workflow_run_interrupted",
                    "runId": 501,
                    "checkpointId": 9001,
                    "payload": {},
                    "observability": {"correlationRefs": {"nodeKey": "confirm"}},
                }
            ],
        )
        pending = _runtime_result(
            status="INTERRUPTED",
            output={
                "interrupt": {"nodeKey": "confirm", "question": "请确认团队询价。"},
                "collected": {"route": "上海到广州", "travel_time": "下周三上午", "passenger_count": "十六"},
            },
            checkpoint_id=9001,
            events=[],
        )
        terminal = _runtime_result(
            status="SUCCEEDED",
            output={
                "final": "group booking complete",
                "collected": {"route": "上海到广州", "travel_time": "下周三上午", "passenger_count": "十六"},
            },
            checkpoint_id=9001,
            events=[
                {
                    "id": 4,
                    "sequence": 4,
                    "type": "workflow_run_completed",
                    "runId": 501,
                    "payload": {"status": "SUCCEEDED"},
                    "observability": {},
                }
            ],
        )
        runtime_v2_service = _FakeRuntimeV2Service([*(dict(pending) for _ in range(44)), terminal])
        adapter = ChatflowSopRuntimeAdapter(
            _FakeWorkflowService(),
            sop_chatflow_ids={"group_booking": 42},
            runtime_v2_service=runtime_v2_service,
            runtime_invocation_gateway=gateway,
        )

        started = adapter.start_sop(_request(message="我们公司十六个人出差", sop_id="group_booking"))
        continued = adapter.continue_sop(
            _request(message="确认团队询价", checkpoint=started.checkpoint, sop_id="group_booking")
        )

        self.assertEqual(continued.status, SopExecutionStatus.WAITING)
        self.assertEqual(continued.current_step, "runtime_running")
        self.assertEqual(continued.collected["passenger_count"], "十六")
        meta = continued.checkpoint.scoped_variables["__chatflow"]
        self.assertEqual(meta["runtimeVersion"], 2)
        self.assertEqual(meta["runtimeRefs"]["resultRef"], "/api/v1/runtime-runs/501/result")


class _FakeRuntimeInvocationGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[Any, ...]] = []
        self.resume_error: BizError | None = None
        self.resume_invocation: dict[str, Any] | None = None
        self.supports_async_resume = True

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

    def resume_and_stream_ref(
        self,
        *,
        owner_id: int,
        run_id: int,
        resume_data: dict[str, Any],
        idempotency_key: str | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("resume_and_stream_ref", run_id, resume_data, idempotency_key, owner_id))
        if self.resume_error is not None:
            raise self.resume_error
        if self.resume_invocation is not None:
            return dict(self.resume_invocation)
        refs = _runtime_refs()
        return {
            "runId": run_id,
            "sessionId": "session-501",
            "status": "RUNNING",
            "runtimeVersion": 2,
            "runtimeMode": "async-durable",
            "runtimeRefs": refs,
            "streamRef": refs["eventStreamRef"],
            "result": None,
            "events": {"list": [], "total": 0},
        }


class _FakeRuntimeV2Service:
    def __init__(self, results: list[dict[str, Any]]) -> None:
        self._results = list(results)
        self.calls: list[int] = []

    def get_result(self, run_id: int) -> dict[str, Any]:
        self.calls.append(run_id)
        if len(self._results) > 1:
            return self._results.pop(0)
        return dict(self._results[0])


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
    sop_id: str = "refund_ticket",
) -> SopExecutionRequest:
    return SopExecutionRequest(
        runtime_session_id=1001,
        runtime_task_id=2002,
        sop_id=sop_id,
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


def _runtime_result(
    *,
    status: str,
    output: dict[str, Any],
    checkpoint_id: int,
    events: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "runId": 501,
        "sessionId": "session-501",
        "status": status,
        "output": output,
        "checkpoint": {"id": checkpoint_id},
        "events": events,
        "runtimeRefs": _runtime_refs(),
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
