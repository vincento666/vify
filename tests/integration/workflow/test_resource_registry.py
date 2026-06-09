import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class WorkflowResourceRegistryTest(unittest.TestCase):
    def test_registry_normalizes_enabled_disabled_unhealthy_and_missing_credential_resources(self) -> None:
        with TestClient(app) as client:
            enabled_mcp = _create_mcp(client, "Registry Enabled MCP", "mock://tools")
            disabled_mcp = _create_mcp(client, "Registry Disabled MCP", "mock://tools")
            client.put(f"/api/v1/mcp-servers/{disabled_mcp['id']}", json={"enabled": 0})
            unhealthy_mcp = _create_mcp(client, "Registry Unhealthy MCP", "http://unsupported.local/mcp")
            missing_credential_mcp = _create_mcp(client, "Registry Missing Credential MCP", "mock://tools?credential=missing")
            published_workflow = _create_workflow(client, "Registry Published Workflow", status="PUBLISHED")
            draft_workflow = _create_workflow(client, "Registry Draft Workflow")

            response = client.get("/api/v1/workflow-resources", params={"flowType": "CHATFLOW"})

        self.assertEqual(response.status_code, 200, response.text)
        resources = response.json()["data"]["list"]
        by_id = {resource["resourceId"]: resource for resource in resources}

        enabled_lookup = by_id[f"mcp:{enabled_mcp['id']}:lookup_order"]
        self.assertEqual(enabled_lookup["resourceType"], "MCP_TOOL")
        self.assertTrue(enabled_lookup["enabled"])
        self.assertEqual(enabled_lookup["credentialStatus"], "PRESENT")
        self.assertEqual(enabled_lookup["healthStatus"], "UP")
        self.assertIn("orderId", enabled_lookup["inputSchema"]["required"])

        disabled_resource = by_id[f"mcp:{disabled_mcp['id']}"]
        self.assertFalse(disabled_resource["enabled"])
        self.assertEqual(disabled_resource["runtimeStatus"], "DISABLED")
        self.assertIn("disabled", disabled_resource["disabledReason"].lower())

        unhealthy_resource = by_id[f"mcp:{unhealthy_mcp['id']}"]
        self.assertFalse(unhealthy_resource["enabled"])
        self.assertEqual(unhealthy_resource["healthStatus"], "DOWN")
        self.assertIn("unsupported", unhealthy_resource["disabledReason"].lower())

        missing_credential_resource = by_id[f"mcp:{missing_credential_mcp['id']}"]
        self.assertFalse(missing_credential_resource["enabled"])
        self.assertEqual(missing_credential_resource["credentialStatus"], "MISSING")
        self.assertIn("credential", missing_credential_resource["disabledReason"].lower())

        subworkflow = by_id[f"workflow:{published_workflow['id']}"]
        self.assertTrue(subworkflow["enabled"])
        self.assertEqual(subworkflow["resourceType"], "SUBWORKFLOW")
        self.assertEqual(subworkflow["runtimeStatus"], "READY")

        draft_subworkflow = by_id[f"workflow:{draft_workflow['id']}"]
        self.assertFalse(draft_subworkflow["enabled"])
        self.assertIn("published", draft_subworkflow["disabledReason"].lower())


def _create_mcp(client: TestClient, name: str, endpoint: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/mcp-servers",
        json={"name": f"{name} {datetime.now().timestamp()}", "endpoint": endpoint, "description": "registry fixture"},
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_workflow(client: TestClient, name: str, status: str = "DRAFT") -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"{name} {datetime.now().timestamp()}",
            "description": "registry fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "output", "output": "ok"}},
            ],
            "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        },
    )
    assert response.status_code == 200, response.text
    workflow = response.json()["data"]
    if status != "DRAFT":
        response = client.put(f"/api/v1/workflows/{workflow['id']}", json={"status": status})
        assert response.status_code == 200, response.text
        workflow = response.json()["data"]
    return workflow


if __name__ == "__main__":
    unittest.main()
