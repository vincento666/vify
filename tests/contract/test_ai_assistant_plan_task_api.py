import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantPlanTaskApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_plan_task",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_message_run_and_inspector_expose_first_class_plan_task_state(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Plan task"}).json()["data"][
                "id"
            ]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "读取 AGENTS.md 并总结",
                    "idempotencyKey": "plan-task-contract-1",
                    "toolCalls": [{"toolName": "read_workspace_file", "toolInput": {"path": "AGENTS.md"}}],
                },
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}")
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector")

        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual(message.json()["data"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(message.json()["data"]["plan"]["id"], f"plan-{run_id}")
        self.assertEqual(run.json()["data"]["input"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(run.json()["data"]["input"]["plan"]["steps"][0]["toolName"], "read_workspace_file")
        self.assertIn("plan.created", [event["type"] for event in events.json()["data"]["list"]])
        self.assertIn("plan.step_started", [event["type"] for event in events.json()["data"]["list"]])
        self.assertIn("task.updated", [event["type"] for event in events.json()["data"]["list"]])
        self.assertIn("plan.step_completed", [event["type"] for event in events.json()["data"]["list"]])
        self.assertIn("task.completed", [event["type"] for event in events.json()["data"]["list"]])
        task_update_payloads = [
            event["payload"] for event in events.json()["data"]["list"] if event["type"] == "task.updated"
        ]
        self.assertTrue(task_update_payloads)
        for payload in task_update_payloads:
            self.assertEqual(payload["toolNames"], ["read_workspace_file"])
            self.assertEqual(payload["plannedTools"], ["read_workspace_file"])
            self.assertEqual(payload["recognizedNeeds"], ["读取 AGENTS.md 并总结"])
            self.assertIn("currentStep", payload)
            self.assertIn("steps", payload)
            self.assertIn("finalResult", payload)

        inspector_data = inspector.json()["data"]
        self.assertEqual(inspector_data["plan"]["planningStrategy"], "auto_lightweight")
        self.assertEqual(inspector_data["plan"]["recognizedNeeds"], ["读取 AGENTS.md 并总结"])
        self.assertEqual(inspector_data["plan"]["steps"][0]["status"], "COMPLETED")
        self.assertEqual(inspector_data["activeTasks"][0]["planId"], f"plan-{run_id}")
        self.assertEqual(inspector_data["activeTasks"][0]["currentStep"]["toolName"], "read_workspace_file")
        self.assertIn("read_workspace_file", inspector_data["activeTasks"][0]["plannedTools"])
        self.assertTrue(inspector_data["activeTasks"][0]["finalResult"])

    def test_plan_only_completes_plan_without_tool_execution(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/ai-assistant/sessions", json={"title": "Plan only"}).json()["data"][
                "id"
            ]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "只规划，不执行",
                    "idempotencyKey": "plan-task-contract-plan-only",
                    "planningStrategy": "plan_only",
                    "toolName": "echo_context",
                },
            )
            run_id = message.json()["data"]["runId"]
            run = client.get(f"/api/v1/ai-assistant/runs/{run_id}")
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector")

        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertEqual(message.json()["data"]["planningStrategy"], "plan_only")
        self.assertEqual(message.json()["data"]["toolCalls"], [])
        self.assertEqual(run.json()["data"]["result"]["plan"]["status"], "COMPLETED")
        self.assertEqual(run.json()["data"]["result"]["plan"]["steps"][0]["status"], "COMPLETED")
        self.assertEqual(inspector.json()["data"]["plan"]["status"], "COMPLETED")
        self.assertEqual(inspector.json()["data"]["plan"]["steps"][0]["status"], "COMPLETED")
        event_types = [event["type"] for event in events.json()["data"]["list"]]
        self.assertIn("plan.created", event_types)
        self.assertIn("plan.step_completed", event_types)
        self.assertIn("task.updated", event_types)
        self.assertIn("task.completed", event_types)
        task_update = next(event for event in events.json()["data"]["list"] if event["type"] == "task.updated")
        self.assertEqual(task_update["payload"]["planningStrategy"], "plan_only")
        self.assertEqual(task_update["payload"]["toolNames"], ["echo_context"])
        self.assertEqual(task_update["payload"]["plannedTools"], ["echo_context"])
        self.assertEqual(task_update["payload"]["recognizedNeeds"], ["只规划，不执行"])
        self.assertEqual(task_update["payload"]["planStatus"], "COMPLETED")
        self.assertEqual(task_update["payload"]["finalResult"], "已生成计划，未执行工具。")
        self.assertEqual(task_update["payload"]["currentStep"]["status"], "COMPLETED")

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
