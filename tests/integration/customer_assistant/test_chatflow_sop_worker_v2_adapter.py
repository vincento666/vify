import json
import time
import unittest
from collections.abc import Iterator
from contextlib import contextmanager

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import get_session
from app.main import app
from app.modules.customer_assistant.domain.scheduler import LocalWorkerScheduler
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.domain.worker_profiles import CustomerAssistantWorkerProfileCatalog
from app.modules.customer_assistant.domain.worker_runtime import CustomerAssistantWorkerRuntime
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker
from app.modules.customer_assistant.domain.workers import StubQaWorker
from app.modules.customer_assistant.web.router import _customer_assistant_sop_adapter
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.workflow.runtime_job_worker import build_runtime_job_worker
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository


class ChatflowSopWorkerV2AdapterTest(unittest.TestCase):
    def test_compatible_chatflow_sop_uses_v2_refs_and_preserves_router_context(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="v2 sop done")
            with _session() as session:
                worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]}))
                result = worker.run(
                    _task(
                        task_id=501,
                        session_id=77,
                        task_key="refund_ticket",
                        worker_ref="refund_ticket",
                        input_snapshot={"route_id": "route-a", "route_turn_id": "turn-1", "intent_key": "refund"},
                    ),
                    "我要退票",
                )
                refs = dict(result.evidence["runtimeRefs"])
                drained = _drain_runtime_job(session, int(refs["runId"]))
            result_response = client.get(str(refs["resultRef"]))

        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertIn("正在后台执行", result.customer_reply_draft)
        self.assertEqual(result.evidence["runtimeVersion"], 2)
        self.assertTrue(result.evidence["chatflowRuntimeRefs"]["eventStreamRef"].endswith("afterSequence=0"))
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.status_code, 200, result_response.text)
        self.assertEqual(result_response.json()["data"]["output"]["final"], "v2 sop done")

    def test_worker_result_projects_runtime_v2_execution_state_for_task_panel(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="v2 task panel")
            unsupported = _create_branching_message_chatflow(client)
            with _session() as session:
                worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]}))
                fallback_worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": unsupported["id"]}))
                result = worker.run(
                    _task(task_id=521, session_id=91, task_key="refund_ticket", worker_ref="refund_ticket"),
                    "我要退票",
                )
                refs = dict(result.evidence["runtimeRefs"])
                drained = _drain_runtime_job(session, int(refs["runId"]))
                fallback = fallback_worker.run(
                    _task(task_id=522, session_id=92, task_key="refund_ticket", worker_ref="refund_ticket"),
                    "我要退票",
                )
            result_response = client.get(str(refs["resultRef"]))

        self.assertEqual(result.evidence["runtimeVersion"], 2)
        run_id = refs["runId"]
        self.assertEqual(result.evidence["chatflowRuntimeRefs"], refs)
        self.assertEqual(refs["statusRef"], f"/api/v1/runtime-runs/{run_id}")
        self.assertEqual(refs["eventsRef"], f"/api/v1/runtime-runs/{run_id}/events")
        self.assertEqual(refs["eventStreamRef"], f"/api/v1/runtime-runs/{run_id}/events/stream?afterSequence=0")
        self.assertEqual(refs["resultRef"], f"/api/v1/runtime-runs/{run_id}/result")
        self.assertEqual(refs["nodesRef"], f"/api/v1/runtime-runs/{run_id}/nodes")
        self.assertEqual(result.evidence["chatflowSession"]["nodesRef"], refs["nodesRef"])
        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertIn("等待 Chatflow runtime", result.evidence["blockingReason"])
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.json()["data"]["output"]["final"], "v2 task panel")

        self.assertIn("Runtime V2 graph is not compatible", fallback.evidence["fallbackReason"])

    def test_async_chatflow_v2_node_events_are_available_from_runtime_stream_after_background_job(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="v2 sop node events")
            with _session() as session:
                worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]}))
                result = worker.run(
                    _task(
                        task_id=511,
                        session_id=88,
                        task_key="refund_ticket",
                        worker_ref="refund_ticket",
                        input_snapshot={
                            "route_id": "route-live",
                            "route_turn_id": "turn-live",
                            "intent_key": "refund",
                        },
                    ),
                    "我要退票",
                )
                refs = dict(result.evidence["runtimeRefs"])
                drained = _drain_runtime_job(session, int(refs["runId"]))

            event_types = [event["type"] for event in result.events]
            first_summary_index = event_types.index("worker_result_received")
            self.assertNotIn("workflow_node_started", event_types[:first_summary_index])
            self.assertEqual(drained["status"], "COMPLETED")

            events_response = client.get(f"/api/v1/runtime-runs/{refs['runId']}/events")
            self.assertEqual(events_response.status_code, 200, events_response.text)
            api_events = events_response.json()["data"]["list"]
            api_event_types = [event["type"] for event in api_events]
            self.assertIn("workflow_node_started", api_event_types)
            self.assertIn("node_status_changed", api_event_types)
            started = next(event for event in api_events if event["type"] == "workflow_run_started")
            self.assertEqual(started["payload"]["callerContext"]["route_id"], "route-live")
            self.assertEqual(started["payload"]["callerContext"]["task_id"], "511")

    def test_llm_chatflow_sop_default_async_exposes_v2_refs_without_falling_back(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="llm v2", node_type="LLM")
            with _session() as session:
                worker = ChatflowSopWorker(
                    _customer_assistant_sop_adapter(
                        session,
                        {"refund_ticket": int(chatflow["id"])},
                        sop_llm_mode="mock",
                    )
                )
                result = worker.run(_task(task_id=502, session_id=78, task_key="refund_ticket", worker_ref="refund_ticket"), "我要退票")
                refs = dict(result.evidence["runtimeRefs"])
                drained = _drain_runtime_job(session, int(refs["runId"]))
            result_response = client.get(str(refs["resultRef"]))

        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertIn("正在后台执行", result.customer_reply_draft)
        self.assertEqual(result.evidence["runtimeVersion"], 2)
        self.assertIn("chatflowRuntimeRefs", result.evidence)
        self.assertTrue(any(event["payload"]["type"] == "chatflow_v2_selected" for event in result.events))
        self.assertFalse(any(event["payload"]["type"] == "chatflow_v2_fallback" for event in result.events))
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.status_code, 200, result_response.text)
        self.assertEqual(result_response.json()["data"]["status"], "SUCCEEDED")
        self.assertIn("LLM mock", json.dumps(result_response.json()["data"]["output"], ensure_ascii=False))

    def test_unsupported_chatflow_sop_falls_back_to_v1_without_fake_v2_refs(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_branching_message_chatflow(client)
            with _session() as session:
                worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]}))
                result = worker.run(_task(task_id=512, session_id=78, task_key="refund_ticket", worker_ref="refund_ticket"), "我要退票")

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertNotIn("chatflowRuntimeRefs", result.evidence)
        self.assertTrue(any(event["payload"]["type"] == "chatflow_v2_fallback" for event in result.events))

    def test_waiting_chatflow_v2_question_prompt_is_customer_draft_and_resume_completes(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            with _session() as session:
                worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]}))
                waiting = worker.run(_task(task_id=503, session_id=79, task_key="refund_ticket", worker_ref="refund_ticket"), "我要退票")
                resumed = worker.run(
                    _task(
                        task_id=503,
                        session_id=79,
                        task_key="refund_ticket",
                        worker_ref="refund_ticket",
                        checkpoint=waiting.checkpoint,
                    ),
                    "订单号是 TK12345",
                )

        self.assertEqual(waiting.status, TaskStatus.WAITING)
        self.assertIn("正在后台执行", waiting.customer_reply_draft)
        self.assertEqual(waiting.checkpoint["currentStep"], "runtime_running")
        self.assertIn(resumed.status, {TaskStatus.WAITING, TaskStatus.COMPLETED})
        self.assertEqual(resumed.evidence["runtimeVersion"], 2)

    def test_v2_waiting_sop_keeps_checkpoint_while_unrelated_task_completes(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            with _session() as session:
                factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
                workers = {
                    "chatflow_sop": ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]})),
                    "stub_qa": StubQaWorker(),
                }
                service = CustomerAssistantService(
                    CustomerAssistantRepository(session),
                    scheduler=LocalWorkerScheduler(workers),
                    async_worker_runtime=CustomerAssistantWorkerRuntime(
                        workers=workers,
                        session_factory=factory,
                        async_worker_types={"chatflow_sop", "stub_qa"},
                        wait_deadline_seconds=2,
                        task_timeout_seconds=5,
                    ),
                    worker_profiles=_legacy_stub_baggage_profiles(),
                )
                assistant_session = service.create_session()

                waiting = service.handle_turn(int(assistant_session["id"]), "我要退票", "066-route-wait")
                wait_run_id = int(waiting["chatflowSession"]["runId"])
                _drain_runtime_job(session, wait_run_id)
                baggage = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "066-route-baggage")
                resumed = service.handle_turn(int(assistant_session["id"]), "订单号是 TK12345", "066-route-resume")
                tasks = service.list_tasks(int(assistant_session["id"]))["list"]
                events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(waiting["taskSummaries"][0]["status"], "WAITING")
        self.assertIn("正在后台执行", waiting["customerReplyDraft"])
        self.assertIn("手提行李", baggage["customerReplyDraft"])
        self.assertIn("order=订单号是 [REDACTED]", resumed["customerReplyDraft"])
        self.assertNotIn("TK12345", resumed["customerReplyDraft"])
        by_key = {task["taskKey"]: task for task in tasks}
        self.assertEqual(by_key["refund_ticket"]["status"], "COMPLETED")
        self.assertEqual(by_key["refund_ticket"]["lastResult"]["evidence"]["runtimeVersion"], 2)
        self.assertEqual(by_key["baggage_qa"]["status"], "COMPLETED")
        chatflow_event = next(event for event in events if event["payload"].get("source") == "chatflow_runtime_v2")
        summary = chatflow_event["observability"]
        self.assertEqual(summary["sourceKind"], "chatflow")
        self.assertEqual(summary["eventMode"], "compatibility_summary")
        refs = summary["correlationRefs"]
        self.assertEqual(refs["assistantRunId"], chatflow_event["runId"])
        self.assertEqual(refs["taskId"], chatflow_event["taskId"])
        self.assertTrue(str(refs["workerRunId"]).startswith("customer-assistant-worker-run-"))
        self.assertGreater(refs["runtimeRunId"], 0)
        self.assertGreater(refs["sourceEventId"], 0)
        self.assertGreater(refs["sourceSequence"], 0)

    def test_customer_assistant_turn_projects_chatflow_session_gateway_refs(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            with _session() as session:
                factory = sessionmaker(bind=session.get_bind(), autoflush=False, autocommit=False, expire_on_commit=False)
                workers = {
                    "chatflow_sop": ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]})),
                }
                service = CustomerAssistantService(
                    CustomerAssistantRepository(session),
                    scheduler=LocalWorkerScheduler(workers),
                    async_worker_runtime=CustomerAssistantWorkerRuntime(
                        workers=workers,
                        session_factory=factory,
                        async_worker_types={"chatflow_sop"},
                        wait_deadline_seconds=2,
                        task_timeout_seconds=5,
                    ),
                )
                assistant_session = service.create_session()
                session_id = int(assistant_session["id"])

                waiting = service.handle_turn(session_id, "我要退票", "198-gateway-start")
                resumed = service.handle_turn(session_id, "订单号是 TK19801", "198-gateway-resume")
                tasks = service.list_tasks(session_id)["list"]

        waiting_gateway = waiting["chatflowSession"]
        resumed_gateway = resumed["chatflowSession"]
        self.assertEqual(waiting_gateway["gatewayMode"], "messages:stream")
        self.assertEqual(waiting_gateway["assistantSessionId"], session_id)
        self.assertEqual(waiting_gateway["currentSopId"], "refund_ticket")
        self.assertTrue(waiting_gateway["sessionId"].startswith(f"customer-assistant-{session_id}-"))
        self.assertEqual(waiting_gateway["conversationId"], waiting_gateway["sessionId"])
        self.assertEqual(waiting_gateway["status"], "WAITING")
        self.assertGreater(waiting_gateway["runId"], 0)
        self.assertIn("/api/v1/runtime-runs/", waiting_gateway["eventStreamRef"])
        self.assertEqual(waiting["recovery"]["sessionId"], session_id)
        self.assertEqual(waiting["recovery"]["chatflowSessionId"], waiting_gateway["sessionId"])
        self.assertGreater(waiting["recovery"]["afterSequence"], 0)
        self.assertIn(
            f"/api/v1/customer-assistant/sessions/{session_id}/events/stream",
            waiting["recovery"]["eventStreamRef"],
        )

        self.assertEqual(resumed_gateway["sessionId"], waiting_gateway["sessionId"])
        self.assertEqual(resumed_gateway["status"], "COMPLETED")
        refund_task = next(task for task in tasks if task["taskKey"] == "refund_ticket")
        self.assertEqual(
            refund_task["lastResult"]["evidence"]["chatflowSession"]["sessionId"],
            waiting_gateway["sessionId"],
        )

    def test_async_chatflow_sop_worker_returns_refs_and_queues_background_runtime_job(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="async v2 done")
            with _session() as session:
                worker = ChatflowSopWorker(
                    _customer_assistant_sop_adapter(
                        session,
                        {"refund_ticket": int(chatflow["id"])},
                        runtime_invocation_mode="async",
                    )
                )
                result = worker.run(
                    _task(task_id=531, session_id=93, task_key="refund_ticket", worker_ref="refund_ticket"),
                    "我要退票",
                )
                refs = dict(result.evidence["runtimeRefs"])
                job = RuntimeJobRepository(session).get_by_run(int(refs["runId"]))
                assert job is not None
                drained = build_runtime_job_worker(
                    session,
                    owner="chatflow",
                    worker_id="chatflow-sop-worker-test",
                ).run_once(job_id=int(job["id"]))

            result_response = client.get(str(refs["resultRef"]))

        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertEqual(result.evidence["runtimeVersion"], 2)
        self.assertEqual(result.evidence["chatflowRuntimeRefs"], refs)
        self.assertEqual(result.evidence["chatflowSession"]["status"], "WAITING")
        self.assertIn("等待 Chatflow runtime", result.evidence["blockingReason"])
        self.assertIn("事件流", result.evidence["operatorAdvice"])
        self.assertIn("eventStreamRef", result.evidence["chatflowSession"])
        self.assertIn("runtime_running", result.operator_recommendation)
        self.assertIn("事件流", result.operator_recommendation)
        self.assertIn("正在后台执行", result.customer_reply_draft)
        self.assertEqual(job["owner_type"], "CHATFLOW")
        self.assertEqual(job["status"], "QUEUED")
        self.assertEqual(drained["status"], "COMPLETED")
        self.assertEqual(result_response.status_code, 200, result_response.text)
        self.assertEqual(result_response.json()["data"]["status"], "SUCCEEDED")
        self.assertEqual(result_response.json()["data"]["output"]["final"], "async v2 done")


def _legacy_stub_baggage_profiles() -> CustomerAssistantWorkerProfileCatalog:
    return CustomerAssistantWorkerProfileCatalog.from_json(
        json.dumps(
            {
                "profiles": [
                    {
                        "profileId": "legacy_baggage_stub",
                        "taskKey": "baggage_qa",
                        "taskType": "QA",
                        "workerType": "stub_qa",
                        "workerRef": "baggage_allowance",
                        "modelPolicyRef": "legacy_stub_qa_model",
                        "promptRef": "baggage_allowance_prompt",
                        "riskPolicyRef": "read_only",
                    }
                ]
            }
        )
    )


def _adapter(session: Session, bindings: dict[str, int]):
    return _customer_assistant_sop_adapter(session, bindings)


def _drain_runtime_job(session: Session, run_id: int) -> dict[str, object]:
    job = RuntimeJobRepository(session).get_by_run(run_id)
    assert job is not None
    return build_runtime_job_worker(
        session,
        owner="chatflow",
        worker_id=f"chatflow-sop-worker-test-{run_id}",
    ).run_once(job_id=int(job["id"]))


@contextmanager
def _session() -> Iterator[Session]:
    yield from get_session()


def _task(
    *,
    task_id: int,
    session_id: int,
    task_key: str,
    worker_ref: str,
    checkpoint: dict[str, object] | None = None,
    input_snapshot: dict[str, object] | None = None,
) -> TaskItem:
    return TaskItem(
        id=task_id,
        session_id=session_id,
        task_key=task_key,
        task_type="sop",
        business_key=task_key,
        short_id=f"T{task_id}",
        status=TaskStatus.PENDING,
        worker_type="chatflow_sop",
        worker_ref=worker_ref,
        checkpoint=dict(checkpoint or {}),
        input_snapshot=dict(input_snapshot or {}),
    )


def _create_message_chatflow(client: TestClient, *, content: str, node_type: str = "MESSAGE") -> dict[str, object]:
    config = {"content": content, "outputVariable": "content"}
    if node_type == "LLM":
        config = {"prompt": content, "outputVariable": "content"}
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"066 Chatflow SOP {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "middle_1", "type": node_type, "name": "Middle", "config": config},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{middle_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "middle_1", "condition": None},
                {"sourceNodeKey": "middle_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_branching_message_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"066 Chatflow SOP Branching {time.time_ns()}",
            "description": "runtime v2 fallback fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_a",
                    "type": "MESSAGE",
                    "name": "Message A",
                    "config": {"content": "fallback branch a", "outputVariable": "content"},
                },
                {
                    "nodeKey": "message_b",
                    "type": "MESSAGE",
                    "name": "Message B",
                    "config": {"content": "fallback branch b", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_a.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "message_b", "condition": None},
                {"sourceNodeKey": "message_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "message_b", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_question_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"066 Chatflow SOP Question {time.time_ns()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Question",
                    "config": {"question": "请提供订单号", "outputVariable": "answer", "answerType": "text"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "order={{question_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
