import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowChannelsTest(unittest.TestCase):
    def test_channels_list_update_and_api_web_test_invocation(self) -> None:
        with TestClient(app) as client:
            chatflow = self._create_echo_chatflow(client)

            channels_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/channels")
            update_response = client.put(
                f"/api/v1/chatflows/{chatflow['id']}/channels/api",
                json={"enabled": True, "displayName": "Production API", "config": {"channelId": "api-prod"}},
            )
            api_test_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/channels/api/test",
                json={
                    "message": "hello channel",
                    "conversationId": f"conv-api-{time.time_ns()}",
                    "userId": "user-api",
                    "channelId": "api-request",
                    "files": [{"name": "invoice.txt"}],
                    "metadata": {"trace": "trace-api"},
                },
            )
            web_test_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/channels/web/test",
                json={"message": "hello web", "userId": "web-user"},
            )

        self.assertEqual(channels_response.status_code, 200)
        channels = channels_response.json()["data"]["list"]
        self.assertEqual({item["channelId"] for item in channels if item["runnable"]}, {"api", "web"})
        api_descriptor = next(item for item in channels if item["channelId"] == "api")
        web_descriptor = next(item for item in channels if item["channelId"] == "web")
        feishu_descriptor = next(item for item in channels if item["channelId"] == "feishu")
        self.assertEqual(api_descriptor["configSchema"]["type"], "object")
        self.assertEqual(api_descriptor["deliveryCapabilities"], {"sync": True, "streaming": True, "files": True, "cards": False})
        self.assertIn("sys.query", api_descriptor["normalizedInputFields"])
        self.assertIn("channel.metadata", api_descriptor["normalizedInputFields"])
        self.assertEqual(web_descriptor["deliveryCapabilities"]["sync"], True)
        self.assertFalse(feishu_descriptor["runnable"])
        self.assertEqual(feishu_descriptor["deliveryCapabilities"], {"sync": False, "streaming": False, "files": False, "cards": False})
        self.assertTrue(feishu_descriptor["unavailableReason"])
        self.assertEqual(update_response.status_code, 200)
        self.assertEqual(update_response.json()["data"]["displayName"], "Production API")

        self.assertEqual(api_test_response.status_code, 200)
        api_result = api_test_response.json()["data"]
        self.assertEqual(api_result["channelId"], "api")
        self.assertEqual(api_result["runtimeInput"]["sys.channel"], "api")
        self.assertEqual(api_result["runtimeInput"]["sys.channel_id"], "api-request")
        self.assertEqual(api_result["runtimeInput"]["sys.user_id"], "user-api")
        self.assertEqual(api_result["runtimeInput"]["sys.files"], [{"name": "invoice.txt"}])
        self.assertEqual(api_result["run"]["status"], "SUCCEEDED")
        self.assertIn("hello channel via api/api-request/user-api", api_result["run"]["output"]["final"])

        self.assertEqual(web_test_response.status_code, 200)
        web_result = web_test_response.json()["data"]
        self.assertEqual(web_result["channelId"], "web")
        self.assertEqual(web_result["runtimeInput"]["sys.channel"], "web")
        self.assertEqual(web_result["runtimeInput"]["sys.user_id"], "web-user")
        self.assertEqual(web_result["run"]["status"], "SUCCEEDED")
        self.assertIn("hello web via web/web-preview/web-user", web_result["run"]["output"]["final"])

    def test_disabled_third_party_channel_shell_rejects_test_invocation(self) -> None:
        with TestClient(app) as client:
            chatflow = self._create_echo_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/channels/feishu/test",
                json={"message": "hello"},
            )

        self.assertEqual(response.status_code, 400)
        self.assertIn("not available", response.json()["message"])

    def test_direct_chatflow_run_normalizes_external_runtime_context(self) -> None:
        with TestClient(app) as client:
            chatflow = self._create_echo_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "message": "hello direct api",
                        "conversationId": f"conv-direct-{time.time_ns()}",
                        "userId": "direct-user",
                        "channelId": "direct-api-request",
                    },
                },
            )
            session_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{response.json()['data']['sessionId']}")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertIn("hello direct api via api/direct-api-request/direct-user", data["output"]["final"])
        self.assertEqual(session_response.status_code, 200)
        session = session_response.json()["data"]
        self.assertEqual(session["channel"], "api")
        self.assertEqual(session["channelId"], "direct-api-request")
        self.assertEqual(session["userId"], "direct-user")

    def _create_echo_chatflow(self, client: TestClient) -> dict:
        response = client.post(
            "/api/v1/chatflows",
            json={
                "name": f"Channel Echo {time.time_ns()}",
                "description": "channel adapter test",
                "nodes": [
                    {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                    {
                        "nodeKey": "end",
                        "type": "END",
                        "name": "End",
                        "config": {
                            "outputVariable": "final",
                            "output": "{{sys.query}} via {{sys.channel}}/{{sys.channel_id}}/{{sys.user_id}} files={{sys.files}}",
                        },
                    },
                ],
                "edges": [{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
            },
        )
        self.assertEqual(response.status_code, 200)
        return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
