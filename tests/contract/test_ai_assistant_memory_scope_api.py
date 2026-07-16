import os
import tempfile
import time
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantMemoryScopeApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import (
            ai_assistant_tables,
            register_ai_assistant_tables,
        )

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_memory_scope_api",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace_a = tempfile.TemporaryDirectory()
        self._workspace_b = tempfile.TemporaryDirectory()
        self._previous_workspace_root = os.environ.get("HIFY_WORKSPACE_ROOT")
        self._previous_worker_delay = getattr(
            app.state,
            "ai_assistant_autonomous_worker_delay_seconds",
            None,
        )
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_a.name
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        if self._previous_worker_delay is None:
            app.state.__dict__["_state"].pop(
                "ai_assistant_autonomous_worker_delay_seconds",
                None,
            )
        else:
            app.state.ai_assistant_autonomous_worker_delay_seconds = self._previous_worker_delay
        if self._previous_workspace_root is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace_root
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace_a.cleanup()
        self._workspace_b.cleanup()

    def test_session_api_uses_current_actor_and_server_workspace_scope(self) -> None:
        with TestClient(app) as client:
            alice_headers = {"X-Hify-Actor-Id": "alice"}
            bob_headers = {"X-Hify-Actor-Id": "bob"}
            created = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
                json={"title": "Alice workspace A"},
            )
            session_id = created.json()["data"]["id"]
            run_id = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                headers=alice_headers,
                json={
                    "message": "scope this run",
                    "idempotencyKey": "scope-run",
                },
            ).json()["data"]["runId"]

            bob_sessions = client.get(
                "/api/v1/ai-assistant/sessions",
                headers=bob_headers,
            ).json()["data"]
            bob_message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                headers=bob_headers,
                json={"message": "foreign", "idempotencyKey": "bob-foreign"},
            )
            bob_delete = client.delete(
                f"/api/v1/ai-assistant/sessions/{session_id}",
                headers=bob_headers,
            )
            os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_b.name
            alice_workspace_b = client.get(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
            ).json()["data"]
            alice_workspace_b_message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                headers=alice_headers,
                json={"message": "foreign workspace", "idempotencyKey": "workspace-foreign"},
            )
            os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace_a.name
            alice_workspace_a = client.get(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
            ).json()["data"]
            bob_run = client.get(
                f"/api/v1/ai-assistant/runs/{run_id}",
                headers=bob_headers,
            )
            alice_run = client.get(
                f"/api/v1/ai-assistant/runs/{run_id}",
                headers=alice_headers,
            )
            bob_run_surfaces = {
                suffix: client.get(
                    f"/api/v1/ai-assistant/runs/{run_id}{suffix}",
                    headers=bob_headers,
                )
                for suffix in (
                    "/inspector",
                    "/audit",
                    "/events",
                    "/snapshot",
                    "/result",
                )
            }

        self.assertEqual(created.status_code, 200)
        self.assertEqual(bob_sessions["total"], 0)
        self.assertEqual(bob_message.status_code, 404)
        self.assertEqual(bob_delete.status_code, 404)
        self.assertEqual(alice_workspace_b["total"], 0)
        self.assertEqual(alice_workspace_b_message.status_code, 404)
        self.assertEqual(alice_workspace_a["total"], 1)
        self.assertEqual(bob_run.status_code, 404)
        self.assertEqual(alice_run.status_code, 200)
        for suffix, response in bob_run_surfaces.items():
            with self.subTest(suffix=suffix):
                self.assertEqual(response.status_code, 404)

    def test_autonomous_worker_preserves_request_scope(self) -> None:
        app.state.ai_assistant_autonomous_worker_delay_seconds = 0
        alice_headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
                json={"title": "Scoped async"},
            ).json()["data"]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages/async",
                headers=alice_headers,
                json={
                    "message": "complete in same scope",
                    "idempotencyKey": "scoped-async",
                },
            ).json()["data"]

            status = started["status"]
            for _ in range(100):
                run = client.get(
                    f"/api/v1/ai-assistant/runs/{started['runId']}",
                    headers=alice_headers,
                ).json()["data"]
                status = run["status"]
                if status in {"COMPLETED", "FAILED", "DENIED", "CANCELLED"}:
                    break
                time.sleep(0.02)

        self.assertEqual(status, "COMPLETED")

    def test_pending_approvals_are_scope_filtered(self) -> None:
        alice_headers = {"X-Hify-Actor-Id": "alice"}
        bob_headers = {"X-Hify-Actor-Id": "bob"}
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=alice_headers,
                json={"title": "Alice approval"},
            ).json()["data"]["id"]
            waiting = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                headers=alice_headers,
                json={
                    "message": "update customer profile",
                    "idempotencyKey": "alice-approval",
                    "approvalMode": "smart_approval",
                    "toolName": "update_customer_profile",
                    "toolInput": {"customerId": "C-1", "field": "tier", "value": "gold"},
                },
            ).json()["data"]
            alice_approvals = client.get(
                "/api/v1/ai-assistant/approvals",
                headers=alice_headers,
            ).json()["data"]["list"]
            bob_approvals = client.get(
                "/api/v1/ai-assistant/approvals",
                headers=bob_headers,
            ).json()["data"]["list"]
            bob_approve = client.post(
                f"/api/v1/ai-assistant/approvals/{alice_approvals[0]['id']}/approve",
                headers=bob_headers,
                json={"actorId": "bob"},
            )

        self.assertEqual(waiting["status"], "WAITING_APPROVAL")
        self.assertEqual(len(alice_approvals), 1)
        self.assertEqual(bob_approvals, [])
        self.assertEqual(bob_approve.status_code, 404)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
