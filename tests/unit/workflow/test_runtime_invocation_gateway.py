import unittest

from app.modules.workflow.domain.runtime_invocation_gateway import RuntimeInvocationGateway


class RuntimeInvocationGatewayTest(unittest.TestCase):
    def test_start_only_returns_unified_refs_without_completing_run(self) -> None:
        service = _FakeRuntimeV2Service()
        gateway = RuntimeInvocationGateway(service)

        result = gateway.start_only(
            owner_id=42,
            input_data={"sys.query": "hello"},
            idempotency_key="start-only",
            version_id=7,
        )

        self.assertEqual(service.calls, [("start_run", 42, {"sys.query": "hello"}, "start-only", 7)])
        self.assertEqual(result["status"], "RUNNING")
        self.assertEqual(result["runtimeRefs"]["runId"], 101)
        self.assertEqual(result["eventStreamRef"], "/api/v1/runtime-runs/101/events/stream?afterSequence=0")
        self.assertEqual(result["events"]["list"], [])
        self.assertIsNone(result["result"])

    def test_start_and_wait_completes_run_and_returns_result_and_events(self) -> None:
        service = _FakeRuntimeV2Service()
        gateway = RuntimeInvocationGateway(service)

        result = gateway.start_and_wait(owner_id=42, input_data={"sys.query": "wait"})

        self.assertEqual(service.calls[0][0], "start_run")
        self.assertIn(("complete_run", 101), service.calls)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["result"]["output"], {"final": "done"})
        self.assertEqual([event["type"] for event in result["events"]["list"]], ["workflow_run_started", "workflow_run_completed"])

    def test_start_and_stream_ref_returns_started_refs_without_waiting_for_completion(self) -> None:
        service = _FakeRuntimeV2Service()
        gateway = RuntimeInvocationGateway(service)

        result = gateway.start_and_stream_ref(owner_id=42, input_data={"sys.query": "stream"})

        self.assertNotIn(("complete_run", 101), service.calls)
        self.assertEqual(result["status"], "RUNNING")
        self.assertEqual(result["streamRef"], "/api/v1/runtime-runs/101/events/stream?afterSequence=0")
        self.assertEqual(result["runtimeRefs"]["eventStreamRef"], result["streamRef"])

    def test_start_and_stream_ref_can_enqueue_background_runtime_job(self) -> None:
        service = _FakeRuntimeV2Service()
        enqueued: list[tuple[int, int]] = []
        gateway = RuntimeInvocationGateway(
            service,
            enqueue_background_run=lambda owner_id, run_id: enqueued.append((owner_id, run_id)) or {"jobId": 901},
        )

        result = gateway.start_and_stream_ref(owner_id=42, input_data={"sys.query": "stream"})

        self.assertEqual(enqueued, [(42, 101)])
        self.assertEqual(result["backgroundJob"], {"jobId": 901})

    def test_resume_and_wait_resumes_same_run_and_returns_unified_result(self) -> None:
        service = _FakeRuntimeV2Service()
        gateway = RuntimeInvocationGateway(service)

        result = gateway.resume_and_wait(run_id=101, resume_data={"answer": "yes"}, idempotency_key="resume")

        self.assertEqual(service.calls, [("resume_run", 101, {"answer": "yes"}, "resume")])
        self.assertEqual(result["runId"], 101)
        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["result"]["output"], {"final": "resumed"})

    def test_resume_and_stream_ref_prepares_and_enqueues_without_executing_run(self) -> None:
        service = _FakeRuntimeV2Service()
        enqueued: list[tuple[int, int, int, dict[str, object], str | None]] = []
        gateway = RuntimeInvocationGateway(
            service,
            enqueue_background_resume=lambda owner_id, run_id, checkpoint_id, resume_data, idempotency_key: (
                enqueued.append((owner_id, run_id, checkpoint_id, resume_data, idempotency_key))
                or {"jobId": 902, "status": "QUEUED"}
            ),
        )

        result = gateway.resume_and_stream_ref(
            owner_id=42,
            run_id=101,
            resume_data={"answer": "yes"},
            idempotency_key="resume-stream",
        )

        self.assertEqual(service.calls, [("prepare_resume", 101, "resume-stream")])
        self.assertEqual(enqueued, [(42, 101, 501, {"answer": "yes"}, "resume-stream")])
        self.assertEqual(result["status"], "INTERRUPTED")
        self.assertEqual(result["streamRef"], "/api/v1/runtime-runs/101/events/stream?afterSequence=0")
        self.assertEqual(result["backgroundJob"], {"jobId": 902, "status": "QUEUED"})


class _FakeRuntimeV2Service:
    def __init__(self) -> None:
        self.calls: list[tuple[object, ...]] = []
        self._status = "RUNNING"
        self._output: dict[str, object] = {}
        self._events = [{"type": "workflow_run_started", "sequence": 1, "runId": 101}]

    def start_run(
        self,
        owner_id: int,
        input_data: dict[str, object],
        idempotency_key: str | None = None,
        version_id: int | None = None,
    ) -> dict[str, object]:
        self.calls.append(("start_run", owner_id, input_data, idempotency_key, version_id))
        return {
            "runId": 101,
            "status": "RUNNING",
            "statusRef": "/api/v1/runtime-runs/101",
            "eventsRef": "/api/v1/runtime-runs/101/events",
            "eventStreamRef": "/api/v1/runtime-runs/101/events/stream?afterSequence=0",
            "nodesRef": "/api/v1/runtime-runs/101/nodes",
            "resultRef": "/api/v1/runtime-runs/101/result",
        }

    def complete_run(self, run_id: int) -> None:
        self.calls.append(("complete_run", run_id))
        self._status = "SUCCEEDED"
        self._output = {"final": "done"}
        self._events.append({"type": "workflow_run_completed", "sequence": 2, "runId": run_id})

    def resume_run(
        self,
        run_id: int,
        resume_data: dict[str, object],
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        self.calls.append(("resume_run", run_id, resume_data, idempotency_key))
        self._status = "SUCCEEDED"
        self._output = {"final": "resumed"}
        return self.get_result(run_id)

    def prepare_resume(self, run_id: int, idempotency_key: str | None = None) -> dict[str, object]:
        self.calls.append(("prepare_resume", run_id, idempotency_key))
        return {
            "runId": run_id,
            "checkpointId": 501,
            "status": "INTERRUPTED",
            "statusRef": f"/api/v1/runtime-runs/{run_id}",
            "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
            "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
            "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
            "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
        }

    def get_result(self, run_id: int) -> dict[str, object]:
        return {
            "runId": run_id,
            "status": self._status,
            "output": dict(self._output),
            "statusRef": f"/api/v1/runtime-runs/{run_id}",
            "eventsRef": f"/api/v1/runtime-runs/{run_id}/events",
            "eventStreamRef": f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0",
            "nodesRef": f"/api/v1/runtime-runs/{run_id}/nodes",
            "resultRef": f"/api/v1/runtime-runs/{run_id}/result",
        }

    def list_events(self, run_id: int, after_sequence: int = 0) -> dict[str, object]:
        return {
            "list": [event for event in self._events if int(event["sequence"]) > after_sequence],
            "total": len(self._events),
        }


if __name__ == "__main__":
    unittest.main()
