import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class ChatflowInformationCollectionTest(unittest.TestCase):
    def test_incomplete_collection_interrupts_with_followup_and_events(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "我叫 Ada"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "INTERRUPTED")
        output = data["output"]
        self.assertEqual(output["interrupt"]["nodeKey"], "info_1")
        self.assertEqual(output["interrupt"]["type"], "INFORMATION_COLLECTION")
        self.assertEqual(output["collected"], {"name": "Ada"})
        self.assertEqual(output["missing"], ["phone"])
        self.assertFalse(output["complete"])
        self.assertIn("phone", output["followup"])
        self.assertEqual([event["type"] for event in output["events"]], ["message_delta", "message_done", "interrupt"])

    def test_followup_template_can_render_missing_and_collected_field_labels(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_airline_collection_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "route:广州飞北京"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "INTERRUPTED")
        output = data["output"]
        self.assertEqual(output["collected"], {"route": "广州飞北京"})
        self.assertEqual(output["missing"], ["travel_time", "passenger_name", "phone"])
        self.assertIn("已记录出发到达城市", output["followup"])
        self.assertIn("出行时间", output["followup"])
        self.assertIn("乘机人姓名", output["followup"])
        self.assertIn("手机号", output["followup"])
        self.assertNotIn("请补充出发到达城市", output["followup"])

    def test_collection_placeholder_values_are_treated_as_missing(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_airline_collection_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": (
                            "route:北京到成都 travel_time:未指定 "
                            "passenger_name:未指定 phone:未指定"
                        )
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "INTERRUPTED")
        output = data["output"]
        self.assertEqual(output["collected"], {"route": "北京到成都"})
        self.assertEqual(output["missing"], ["travel_time", "passenger_name", "phone"])
        self.assertIn("请补充出行时间、乘机人姓名、手机号", output["followup"])

    def test_resume_collection_merges_state_writes_scope_and_continues(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "手机号 13800138000",
                        "resume": {
                            "info_1": {
                                "answer": "手机号 13800138000",
                                "collected": {"name": "Ada"},
                            }
                        },
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "Ada|13800138000|Ada"})

    def test_history_awareness_extracts_from_previous_messages(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client, include_history=True)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "手机号 13800138000",
                        "history": [{"role": "user", "content": "姓名 Ada"}],
                    }
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "Ada|13800138000|Ada"})

    def test_selected_node_complete_run_returns_structured_collection(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/nodes/info_1/runs",
                json={"input": {"sys.query": "我叫 Ada 手机号 13800138000"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        output = response.json()["data"]["output"]
        self.assertTrue(output["complete"])
        self.assertEqual(output["missing"], [])
        self.assertEqual(output["collected"], {"name": "Ada", "phone": "13800138000"})


def _create_information_collection_chatflow(client: TestClient, include_history: bool = False) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Information Collection Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "info_1",
                    "type": "INFORMATION_COLLECTION",
                    "name": "信息收集",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "profile",
                        "collectionKey": "profile",
                        "includeHistory": include_history,
                        "maxRounds": 3,
                        "streamOutput": "enabled",
                        "fields": [
                            {
                                "name": "name",
                                "type": "string",
                                "required": True,
                                "description": "姓名",
                                "targetScope": "conversation",
                                "targetVariable": "customer_name",
                            },
                            {
                                "name": "phone",
                                "type": "string",
                                "required": True,
                                "description": "手机号",
                            },
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "{{info_1.name}}|{{info_1.phone}}|{{conversation.customer_name}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_1", "condition": None},
                {"sourceNodeKey": "info_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_airline_collection_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Airline Collection Chatflow {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "info_1",
                    "type": "INFORMATION_COLLECTION",
                    "name": "信息收集",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "collected",
                        "collectionKey": "collected",
                        "maxRounds": 3,
                        "streamOutput": "enabled",
                        "followupTemplate": "我先帮你进入机票预订。{{collected_notice}}请补充{{missing_labels}}。",
                        "fields": [
                            {"name": "route", "type": "string", "required": True, "description": "出发到达城市"},
                            {"name": "travel_time", "type": "string", "required": True, "description": "出行时间"},
                            {"name": "passenger_name", "type": "string", "required": True, "description": "乘机人姓名"},
                            {"name": "phone", "type": "string", "required": True, "description": "手机号"},
                        ],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_1", "condition": None},
                {"sourceNodeKey": "info_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
