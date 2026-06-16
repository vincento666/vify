import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class OpsSecurityPolishTest(unittest.TestCase):
    def test_audit_handoff_sla_and_sanitized_snapshots(self) -> None:
        with TestClient(app) as client:
            workflow = self._create_workflow(client, "audit-v1")
            publish_v1 = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            self._update_workflow_output(client, workflow["id"], "audit-v2")
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            client.post(f"/api/v1/workflows/{workflow['id']}/versions/{publish_v1['id']}/rollback")

            chatflow = self._create_handoff_chatflow(client, sla_minutes=1)
            client.put(
                f"/api/v1/chatflows/{chatflow['id']}/channels/web",
                json={"displayName": "Web Audit", "enabled": True, "config": {"channelId": "web-audit"}},
            )
            conversation_id = f"handoff-sec-{time.time_ns()}"
            run_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "需要人工，apiKey=sk-secret password=hunter2",
                        "sys.conversation_id": conversation_id,
                        "sys.user_id": "secure-user",
                        "sys.channel": "web",
                    }
                },
            )
            self.assertEqual(run_response.status_code, 200)

            handoffs = client.get("/api/v1/handoffs", params={"pageSize": 100}).json()["data"]["list"]
            ticket = next(item for item in handoffs if item["conversationId"] == conversation_id)
            self.assertEqual(ticket["slaState"], "warning")
            transcript_text = str(ticket["transcriptSnapshot"])
            self.assertNotIn("sk-secret", transcript_text)
            self.assertNotIn("hunter2", transcript_text)
            self.assertIn("***", transcript_text)

            assign_response = client.post(f"/api/v1/handoffs/{ticket['id']}/assign", json={"assignee": "alice"})
            return_response = client.post(f"/api/v1/handoffs/{ticket['id']}/return-to-bot")

            close_chatflow = self._create_handoff_chatflow(client, sla_minutes=1)
            close_conversation_id = f"handoff-close-{time.time_ns()}"
            client.post(
                f"/api/v1/chatflows/{close_chatflow['id']}/runs",
                json={"input": {"sys.query": "close me", "sys.conversation_id": close_conversation_id}},
            )
            close_ticket = next(
                item
                for item in client.get("/api/v1/handoffs", params={"pageSize": 100}).json()["data"]["list"]
                if item["conversationId"] == close_conversation_id
            )
            close_response = client.post(f"/api/v1/handoffs/{close_ticket['id']}/close", json={"resolution": "resolved"})

            audit = client.get("/api/v1/audit-records", params={"pageSize": 200}).json()["data"]["list"]

        self.assertEqual(assign_response.status_code, 200)
        self.assertEqual(assign_response.json()["data"]["status"], "assigned")
        self.assertEqual(return_response.status_code, 200)
        self.assertEqual(return_response.json()["data"]["status"], "returned_to_bot")
        self.assertEqual(close_response.status_code, 200)
        self.assertEqual(close_response.json()["data"]["status"], "closed")
        actions = {item["action"] for item in audit}
        self.assertIn("WORKFLOW_PUBLISH", actions)
        self.assertIn("WORKFLOW_ROLLBACK", actions)
        self.assertIn("CHATFLOW_CHANNEL_UPDATE", actions)
        self.assertIn("HANDOFF_ASSIGN", actions)
        self.assertIn("HANDOFF_RETURN_TO_BOT", actions)
        self.assertIn("HANDOFF_CLOSE", actions)

    def test_disabled_channel_test_records_delivery_failure(self) -> None:
        with TestClient(app) as client:
            chatflow = self._create_handoff_chatflow(client, sla_minutes=1)
            client.put(
                f"/api/v1/chatflows/{chatflow['id']}/channels/web",
                json={"displayName": "Disabled Web", "enabled": False, "config": {"channelId": "web-disabled"}},
            )
            failure = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/channels/web/test",
                json={"message": "hello", "conversationId": f"disabled-{time.time_ns()}"},
            )
            audit = client.get(
                "/api/v1/audit-records",
                params={"resourceType": "CHATFLOW_CHANNEL", "pageSize": 50},
            ).json()["data"]["list"]
            metrics = client.get("/api/v1/observe/metrics").json()["data"]

        self.assertEqual(failure.status_code, 400)
        failed = next(item for item in audit if item["action"] == "CHANNEL_DELIVERY_FAILED")
        self.assertEqual(failed["status"], "failed")
        self.assertEqual(failed["metadata"]["deliveryStatus"], "failed")
        self.assertIn("disabled", failed["metadata"]["error"])
        self.assertGreaterEqual(metrics["channelDeliveryFailures"], 1)

    def _create_workflow(self, client: TestClient, output: str) -> dict:
        response = client.post(
            "/api/v1/workflows",
            json={
                "name": f"Audit Workflow {time.time_ns()}",
                "description": "",
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": output}},
                ],
                "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]

    def _update_workflow_output(self, client: TestClient, workflow_id: int, output: str) -> None:
        response = client.put(
            f"/api/v1/workflows/{workflow_id}",
            json={
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": output}},
                ],
                "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
            },
        )
        self.assertEqual(response.status_code, 200)

    def _create_handoff_chatflow(self, client: TestClient, sla_minutes: int) -> dict:
        response = client.post(
            "/api/v1/chatflows",
            json={
                "name": f"Security Handoff {time.time_ns()}",
                "description": "",
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {
                        "nodeKey": "handoff_1",
                        "type": "TRANSFER_TO_HUMAN",
                        "name": "Handoff",
                        "config": {
                            "queue": "security",
                            "message": "转人工",
                            "slaMinutes": sla_minutes,
                        },
                    },
                    {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
                ],
                "edges": [
                    {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
                    {"sourceNodeKey": "handoff_1", "targetNodeKey": "end", "condition": None},
                ],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
