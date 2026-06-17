import time
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


def _host_headers(tenant_id: str) -> dict[str, str]:
    return {
        "X-Hify-Actor-Id": f"operator-{tenant_id}",
        "X-Hify-Actor-Name": f"Operator {tenant_id}",
        "X-Hify-Tenant-Id": tenant_id,
        "X-Hify-Org-Id": tenant_id,
        "X-Hify-Source": "embedded-demo-shell",
        "X-Hify-Permissions": "customer_assistant:read,customer_assistant:operate",
        "X-Request-Id": f"req-{tenant_id}",
    }


class CustomerAssistantSpawnSubAgentTenantAccessTest(unittest.TestCase):
    def setUp(self) -> None:
        self._database = mysql8_unittest_database(self, "customer_assistant_spawn_access")
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(runtime_lab_sop_chatflow_ids=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_spawn_sub_agent_rejects_cross_tenant_session(self) -> None:
        tenant_a_headers = _host_headers("tenant-spawn-a")
        tenant_b_headers = _host_headers("tenant-spawn-b")
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/customer-assistant/sessions",
                json={"context": {}},
                headers=tenant_a_headers,
            )
            self.assertEqual(created.status_code, 200, created.text)
            session_id = int(created.json()["data"]["id"])

            response = client.post(
                "/api/v1/customer-assistant/harness/spawn-sub-agent",
                json={
                    "tool": "spawn_sub_agent",
                    "arguments": {
                        "agentType": "customer_assistant",
                        "sessionId": session_id,
                        "input": {"message": "帮我继续退票流程", "actor": "operator"},
                        "eventLevel": "L1",
                    },
                },
                headers=tenant_b_headers,
            )

        self.assertEqual(response.status_code, 403, response.text)
        self.assertEqual(response.json()["code"], 403)
        self.assertIn("another tenant", response.json()["message"])

    def test_background_sub_agent_run_preserves_host_context_audit(self) -> None:
        tenant_headers = _host_headers("tenant-spawn-audit")
        with TestClient(app) as client:
            created = client.post(
                "/api/v1/customer-assistant/sessions",
                json={"context": {}},
                headers=tenant_headers,
            )
            self.assertEqual(created.status_code, 200, created.text)
            session_id = int(created.json()["data"]["id"])

            response = client.post(
                "/api/v1/customer-assistant/harness/spawn-sub-agent",
                json={
                    "tool": "spawn_sub_agent",
                    "arguments": {
                        "agentType": "customer_assistant",
                        "sessionId": session_id,
                        "input": {"message": "帮我查退票状态", "actor": "operator"},
                        "eventLevel": "L1",
                    },
                },
                headers=tenant_headers,
            )
            self.assertEqual(response.status_code, 200, response.text)
            run_id = int(response.json()["data"]["runId"])

            for _ in range(20):
                run = client.get(f"/api/v1/customer-assistant/runs/{run_id}", headers=tenant_headers)
                self.assertEqual(run.status_code, 200, run.text)
                if run.json()["data"]["status"] == "completed":
                    break
                time.sleep(0.05)
            events = client.get(
                f"/api/v1/customer-assistant/sessions/{session_id}/events",
                headers=tenant_headers,
            ).json()["data"]["list"]

        started = next(event for event in events if event["type"] == "sub_agent_started")
        self.assertEqual(started["actor"], "operator")
        context_snapshot = next(
            event
            for event in events
            if event["type"] == "session_context_snapshot" and event["payload"].get("hostContext")
        )
        self.assertEqual(context_snapshot["payload"]["hostContext"]["tenantId"], "tenant-spawn-audit")
        self.assertIn("customer_assistant:operate", context_snapshot["payload"]["hostContext"]["permissions"])

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session
