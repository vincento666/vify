import tempfile
import unittest
from collections.abc import Generator
import json
import time
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from app.main import app
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "customer_assistant_api.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        register_customer_assistant_tables()
        Base.metadata.create_all(bind=self._engine, tables=customer_assistant_tables())
        self._factory = sessionmaker(bind=self._engine, autoflush=False, autocommit=False, expire_on_commit=False)
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_session_turn_tasks_events_actions_and_idempotent_replay(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={"context": {"customerId": "C-1"}})
            session_id = created.json()["data"]["id"]
            first = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "turn-1"},
            )
            replay = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "turn-1"},
            )
            client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "订单号 TK-100", "idempotencyKey": "turn-2"},
            )
            completed = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "确认", "idempotencyKey": "turn-3"},
            )
            tasks = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks")
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events")
            action_id = completed.json()["data"]["proposedActions"][0]["id"]
            confirmed = client.post(f"/api/v1/customer-assistant/proposed-actions/{action_id}/confirm")
            rejected = client.post(f"/api/v1/customer-assistant/proposed-actions/{action_id}/reject")

        self.assertEqual(created.status_code, 200)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["code"], 200)
        self.assertEqual(first.json()["message"], "success")
        self.assertEqual(first.json()["data"]["taskSummaries"][0]["taskKey"], "refund_ticket")
        self.assertEqual(replay.json()["data"]["runId"], first.json()["data"]["runId"])
        self.assertEqual(replay.json()["data"]["replayed"], True)
        self.assertEqual(completed.json()["data"]["proposedActions"][0]["status"], "PENDING")
        self.assertEqual([task["taskKey"] for task in tasks.json()["data"]["list"]], ["refund_ticket"])
        self.assertEqual(tasks.json()["data"]["list"][0]["status"], "COMPLETED")
        self.assertEqual(
            [event["sequence"] for event in events.json()["data"]["list"]],
            list(range(1, events.json()["data"]["total"] + 1)),
        )
        self.assertEqual(confirmed.json()["data"]["status"], "CONFIRMED")
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(rejected.json()["code"], 400)

    def test_bound_refund_sop_uses_chatflow_adapter_instead_of_fake_sop(self) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids="refund_ticket:999")

        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "bound-real-chatflow"},
            )

        self.assertEqual(turn.status_code, 200)
        task = turn.json()["data"]["taskSummaries"][0]
        self.assertEqual(task["taskKey"], "refund_ticket")
        self.assertEqual(task["status"], "FAILED")
        self.assertEqual(task["lastResult"]["status"], "FAILED")
        self.assertEqual(task["lastResult"]["error"]["code"], "CHATFLOW_START_FAILED")

    def test_turn_actor_is_persisted_validated_and_part_of_idempotency(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            operator_turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "same-text-actor", "actor": "operator"},
            )
            customer_turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "same-text-actor-customer", "actor": "customer"},
            )
            default_turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "行李额度是多少", "idempotencyKey": "default-actor"},
            )
            invalid_actor = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "系统触发", "idempotencyKey": "bad-actor", "actor": "robot"},
            )
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events")

        self.assertEqual(operator_turn.status_code, 200)
        self.assertEqual(customer_turn.status_code, 200)
        self.assertNotEqual(operator_turn.json()["data"]["runId"], customer_turn.json()["data"]["runId"])
        self.assertEqual(operator_turn.json()["data"]["replyType"], "OPERATOR_RECOMMENDATION")
        self.assertEqual(operator_turn.json()["data"]["taskSummaries"], [])
        self.assertEqual(default_turn.status_code, 200)
        self.assertEqual(invalid_actor.status_code, 422)

        event_rows = events.json()["data"]["list"]
        run_started_by_run = {row["runId"]: row for row in event_rows if row["type"] == "run_started"}
        self.assertEqual(run_started_by_run[operator_turn.json()["data"]["runId"]]["actor"], "operator")
        self.assertEqual(run_started_by_run[customer_turn.json()["data"]["runId"]]["actor"], "customer")
        self.assertEqual(run_started_by_run[default_turn.json()["data"]["runId"]]["actor"], "customer")
        self.assertEqual(
            run_started_by_run[operator_turn.json()["data"]["runId"]]["payload"]["actor"],
            "operator",
        )
        self.assertEqual(
            run_started_by_run[operator_turn.json()["data"]["runId"]]["payload"]["turnMode"],
            "operator_recommendation_turn",
        )

        with self._factory() as session:
            runs = session.execute(
                Base.metadata.tables["customer_assistant_run"].select().order_by(
                    Base.metadata.tables["customer_assistant_run"].c.id.asc()
                )
            ).mappings().all()
            tasks = session.execute(
                Base.metadata.tables["customer_assistant_task"].select().order_by(
                    Base.metadata.tables["customer_assistant_task"].c.id.asc()
                )
            ).mappings().all()

        self.assertEqual(runs[0]["input_payload"]["actor"], "operator")
        self.assertEqual(runs[0]["input_payload"]["turnMode"], "operator_recommendation_turn")
        self.assertEqual(runs[1]["input_payload"]["actor"], "customer")
        self.assertFalse(any(task["input_snapshot_json"].get("actor") == "operator" for task in tasks))
        self.assertTrue(any(task["input_snapshot_json"].get("actor") == "customer" for task in tasks))

    def test_events_stream_replays_persisted_events_and_resumes_after_sequence(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "stream-replay"},
            )
            listed = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events")
            with client.stream(
                "GET",
                f"/api/v1/customer-assistant/sessions/{session_id}/events/stream?afterSequence=0&_testLimit=2",
            ) as response:
                first_events = _read_sse_events(response, 2)
            with client.stream(
                "GET",
                f"/api/v1/customer-assistant/sessions/{session_id}/events/stream?afterSequence=1&_testLimit=1",
            ) as response:
                resumed_events = _read_sse_events(response, 1)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertEqual(first_events[0]["sequence"], 1)
        self.assertEqual(first_events[0]["type"], listed.json()["data"]["list"][0]["type"])
        self.assertEqual(first_events[1]["sequence"], 2)
        self.assertEqual(resumed_events[0]["sequence"], 2)

    def test_events_stream_sends_idle_heartbeat(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            with client.stream(
                "GET",
                f"/api/v1/customer-assistant/sessions/{session_id}/events/stream"
                "?afterSequence=0&heartbeatMs=100&_testHeartbeatLimit=1",
            ) as response:
                first_line = next(response.iter_lines())

        self.assertEqual(response.status_code, 200)
        self.assertEqual(first_line, ": heartbeat")

    def test_baggage_turn_returns_fetchable_async_worker_refs(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            first = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "行李额度是多少", "idempotencyKey": "worker-async-refs"},
            )
            replay = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "行李额度是多少", "idempotencyKey": "worker-async-refs"},
            )
            task = first.json()["data"]["taskSummaries"][0]
            refs = task["workerAsyncRefs"]
            status = client.get(refs["workerStatusRef"])
            result = client.get(refs["workerResultRef"])
            events = client.get(refs["workerEventsRef"])

        self.assertEqual(first.status_code, 200)
        self.assertEqual(task["taskKey"], "baggage_qa")
        self.assertTrue(refs["supported"])
        self.assertTrue(refs["workerRunId"].startswith("customer-assistant-worker-run-"))
        self.assertEqual(replay.json()["data"]["taskSummaries"][0]["workerAsyncRefs"]["workerRunId"], refs["workerRunId"])

        self.assertEqual(status.status_code, 200)
        self.assertEqual(status.json()["data"]["status"], "COMPLETED")
        self.assertEqual(status.json()["data"]["parentRunId"], first.json()["data"]["runId"])
        self.assertEqual(status.json()["data"]["taskId"], task["id"])
        self.assertEqual(status.json()["data"]["workerType"], "stub_qa")

        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["data"]["status"], "COMPLETED")
        self.assertIn("手提行李", result.json()["data"]["result"]["customerReplyDraft"])

        event_rows = events.json()["data"]["list"]
        self.assertEqual(events.status_code, 200)
        self.assertEqual([row["sequence"] for row in event_rows], list(range(1, len(event_rows) + 1)))
        self.assertIn("worker_run_queued", [row["type"] for row in event_rows])
        self.assertIn("worker_run_completed", [row["type"] for row in event_rows])

    def test_worker_cancel_records_unsupported_event_without_rewriting_completed_result(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/customer-assistant/sessions", json={}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "行李额度是多少", "idempotencyKey": "worker-cancel"},
            ).json()["data"]
            refs = turn["taskSummaries"][0]["workerAsyncRefs"]

            cancelled = client.post(f"{refs['workerStatusRef']}/cancel")
            status = client.get(refs["workerStatusRef"])
            result = client.get(refs["workerResultRef"])
            events = client.get(refs["workerEventsRef"])

        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json()["data"]["status"], "cancel_unsupported")
        self.assertEqual(status.json()["data"]["status"], "COMPLETED")
        self.assertIn("手提行李", result.json()["data"]["result"]["customerReplyDraft"])
        event_types = [row["type"] for row in events.json()["data"]["list"]]
        self.assertIn("worker_cancel_requested", event_types)
        self.assertIn("worker_cancel_unsupported", event_types)

    def test_pending_async_worker_can_be_refreshed_through_api(self) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(
            runtime_lab_sop_chatflow_ids=None,
            customer_assistant_stub_qa_delay_seconds=0.12,
            customer_assistant_worker_wait_deadline_seconds=0.01,
            customer_assistant_worker_timeout_seconds=1.0,
        )
        with TestClient(app) as client:
            session_id = client.post("/api/v1/customer-assistant/sessions", json={}).json()["data"]["id"]
            turn = client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "行李额度是多少", "idempotencyKey": "pending-api"},
            ).json()["data"]
            refs = turn["taskSummaries"][0]["workerAsyncRefs"]
            worker_started = client.get(refs["workerStatusRef"]).json()["data"]
            time.sleep(0.18)
            refreshed = client.post(f"/api/v1/customer-assistant/sessions/{session_id}/worker-results/refresh")

        self.assertEqual(turn["taskSummaries"][0]["status"], "RUNNING")
        self.assertEqual(worker_started["status"], "RUNNING")
        self.assertIn("required worker evidence is pending", " ".join(turn["warnings"]))
        self.assertEqual(refreshed.status_code, 200)
        self.assertEqual(refreshed.json()["data"]["consumed"], 1)
        self.assertEqual(refreshed.json()["data"]["tasks"][0]["status"], "COMPLETED")

    def test_confirmed_proposed_action_can_execute_once_through_mock_executor(self) -> None:
        with TestClient(app) as client:
            created = client.post("/api/v1/customer-assistant/sessions", json={})
            session_id = created.json()["data"]["id"]
            client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "我要退票", "idempotencyKey": "exec-1"},
            )
            client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "订单号 TK-100 手机号 13800138000 乘机人 张三", "idempotencyKey": "exec-2"},
            )
            client.post(
                f"/api/v1/customer-assistant/sessions/{session_id}/turns",
                json={"message": "确认", "idempotencyKey": "exec-3"},
            )
            action_id = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/tasks").json()["data"]["list"][0][
                "proposedActions"
            ][0]["id"]

            pending_execute = client.post(f"/api/v1/customer-assistant/proposed-actions/{action_id}/execute")
            confirmed = client.post(f"/api/v1/customer-assistant/proposed-actions/{action_id}/confirm")
            executed = client.post(f"/api/v1/customer-assistant/proposed-actions/{action_id}/execute")
            events = client.get(f"/api/v1/customer-assistant/sessions/{session_id}/events")

        self.assertEqual(pending_execute.status_code, 400)
        self.assertEqual(confirmed.json()["data"]["status"], "CONFIRMED")
        self.assertEqual(executed.status_code, 200)
        self.assertEqual(executed.json()["data"]["status"], "EXECUTED")
        self.assertEqual(executed.json()["data"]["result"]["executorRef"], "refund_submit_mock")
        self.assertIn("proposed_action_executed", [event["type"] for event in events.json()["data"]["list"]])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _read_sse_events(response, count: int) -> list[dict[str, object]]:
    events: list[dict[str, object]] = []
    for line in response.iter_lines():
        if not line.startswith("data: "):
            continue
        events.append(json.loads(line.removeprefix("data: ")))
        if len(events) >= count:
            break
    return events


if __name__ == "__main__":
    unittest.main()
