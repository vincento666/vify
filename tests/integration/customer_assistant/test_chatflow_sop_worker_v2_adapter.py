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
from app.modules.customer_assistant.domain.worker_runtime import CustomerAssistantWorkerRuntime
from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus
from app.modules.customer_assistant.domain.workers import ChatflowSopWorker
from app.modules.customer_assistant.domain.workers import StubQaWorker
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


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

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertEqual(result.customer_reply_draft, "v2 sop done")
        self.assertEqual(result.evidence["runtimeVersion"], 2)
        self.assertTrue(result.evidence["chatflowRuntimeRefs"]["eventStreamRef"].endswith("afterSequence=0"))
        self.assertTrue(any(event["payload"]["type"] == "workflow_run_started" for event in result.events))
        started = next(event for event in result.events if event["payload"]["type"] == "workflow_run_started")
        self.assertEqual(started["payload"]["callerContext"]["route_id"], "route-a")
        self.assertEqual(started["payload"]["callerContext"]["task_id"], "501")

    def test_chatflow_v2_node_events_are_first_class_worker_events_before_compatibility_summary(self) -> None:
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

            event_types = [event["type"] for event in result.events]
            first_summary_index = event_types.index("worker_result_received")
            node_started_index = event_types.index("workflow_node_started")
            status_changed_index = event_types.index("node_status_changed")

            self.assertLess(node_started_index, first_summary_index)
            self.assertLess(status_changed_index, first_summary_index)
            node_event = result.events[node_started_index]
            self.assertEqual(node_event["source"], "chatflow_runtime_v2")
            self.assertEqual(node_event["payload"]["eventMode"], "live")
            self.assertEqual(node_event["payload"]["sourceKind"], "chatflow")
            self.assertEqual(node_event["payload"]["callerContext"]["route_id"], "route-live")
            self.assertGreater(node_event["payload"]["sourceEventId"], 0)
            self.assertGreater(node_event["payload"]["sourceSequence"], 0)
            self.assertEqual(node_event["payload"]["runtimeRunId"], result.evidence["chatflowRuntimeRefs"]["runId"])

            events_response = client.get(f"/api/v1/runtime-runs/{node_event['payload']['runtimeRunId']}/events")
            self.assertEqual(events_response.status_code, 200, events_response.text)
            api_event_types = [event["type"] for event in events_response.json()["data"]["list"]]
            self.assertIn("workflow_node_started", api_event_types)
            self.assertIn("node_status_changed", api_event_types)

    def test_unsupported_chatflow_sop_falls_back_to_v1_without_fake_v2_refs(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, content="fallback", node_type="LLM")
            with _session() as session:
                worker = ChatflowSopWorker(_adapter(session, {"refund_ticket": chatflow["id"]}))
                result = worker.run(_task(task_id=502, session_id=78, task_key="refund_ticket", worker_ref="refund_ticket"), "我要退票")

        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertIn("LLM mock", result.customer_reply_draft)
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
        self.assertEqual(waiting.customer_reply_draft, "请提供订单号")
        self.assertEqual(waiting.checkpoint["pendingPrompt"], "请提供订单号")
        self.assertEqual(resumed.status, TaskStatus.COMPLETED)
        self.assertEqual(resumed.customer_reply_draft, "order=订单号是 TK12345")

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
                )
                assistant_session = service.create_session()

                waiting = service.handle_turn(int(assistant_session["id"]), "我要退票", "066-route-wait")
                baggage = service.handle_turn(int(assistant_session["id"]), "行李额度是多少", "066-route-baggage")
                resumed = service.handle_turn(int(assistant_session["id"]), "订单号是 TK12345", "066-route-resume")
                tasks = service.list_tasks(int(assistant_session["id"]))["list"]
                events = service.list_events(int(assistant_session["id"]))["list"]

        self.assertEqual(waiting["taskSummaries"][0]["status"], "WAITING")
        self.assertIn("请提供订单号", waiting["customerReplyDraft"])
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


def _adapter(session: Session, bindings: dict[str, int]) -> ChatflowSopRuntimeAdapter:
    return ChatflowSopRuntimeAdapter(
        WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            chatflow_state_repository=ChatflowStateRepository(session),
        ),
        sop_chatflow_ids=bindings,
        fallback_adapter=FakeSopRuntimeAdapter(),
        runtime_v2_service=ChatflowRuntimeV2Service(
            WorkflowRepository(session),
            ChatflowStateRepository(session),
            completion_delay_seconds=0,
        ),
    )


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
