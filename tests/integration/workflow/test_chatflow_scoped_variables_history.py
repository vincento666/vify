import time
import unittest

from fastapi.testclient import TestClient

from app.main import app


class ChatflowScopedVariablesHistoryIntegrationTest(unittest.TestCase):
    def test_resume_persists_conversation_variable_scope_in_session_state(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_variable_resume_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp)
            run_id = int(interrupted["runId"])
            event_id = int(interrupted["events"][-1]["id"])
            resumed = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"answer": "refund"}},
            )
            session = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/{interrupted['sessionId']}")

        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(resumed.json()["data"]["output"], {"final": "topic=refund"})
        self.assertEqual(session.status_code, 200, session.text)
        self.assertEqual(session.json()["data"]["variables"]["conversation"]["topic"], "refund")

    def test_include_history_reads_bounded_persisted_session_events(self) -> None:
        stamp = time.time_ns()
        conversation_id = f"conv-{stamp}"
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, stamp)
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "订单问题", "sys.conversation_id": conversation_id}},
            )
            self.assertEqual(first.status_code, 200, first.text)
            _replace_with_history_collection_chatflow(client, int(chatflow["id"]), stamp)
            second = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "手机号 13800138000", "sys.conversation_id": conversation_id}},
            )

        self.assertEqual(second.status_code, 200, second.text)
        data = second.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED", data)
        self.assertEqual(data["output"]["final"], "Ada|13800138000")

    def test_chatflow_start_history_retention_limits_persisted_history(self) -> None:
        stamp = time.time_ns()
        conversation_id = f"conv-retention-{stamp}"
        with TestClient(app) as client:
            chatflow = _create_message_chatflow(client, stamp, content_template="{{start.sys.query}}")
            first = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "姓名 Ada", "sys.conversation_id": conversation_id}},
            )
            second = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "手机号 13800138000", "sys.conversation_id": conversation_id}},
            )
            self.assertEqual(first.status_code, 200, first.text)
            self.assertEqual(second.status_code, 200, second.text)
            _replace_with_history_collection_chatflow(client, int(chatflow["id"]), stamp, history_retention_rounds=1)
            retained = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "继续", "sys.conversation_id": conversation_id}},
            )

        self.assertEqual(retained.status_code, 200, retained.text)
        data = retained.json()["data"]
        self.assertEqual(data["status"], "INTERRUPTED", data)
        self.assertEqual(data["output"]["missing"], ["name"])
        self.assertEqual(data["output"]["interrupt"]["missing"], ["name"])

    def test_scoped_input_variables_render_and_persist_with_session_expiration(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_scope_input_chatflow(client, stamp)
            run = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={
                    "input": {
                        "sys.query": "refund",
                        "sys.conversation_id": f"scope-{stamp}",
                        "user.tier": "vip",
                        "channel.name": "web",
                        "global.locale": "zh-CN",
                        "externalId": "ticket-0183",
                    }
                },
            )
            session = client.get(f"/api/v1/chatflows/{chatflow['id']}/sessions/scope-{stamp}")

        self.assertEqual(run.status_code, 200, run.text)
        data = run.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED", data)
        self.assertEqual(data["output"]["final"], "refund|vip|web|zh-CN|ticket-0183")
        self.assertEqual(session.status_code, 200, session.text)
        session_data = session.json()["data"]
        self.assertEqual(session_data["variables"]["sys"]["query"], "refund")
        self.assertEqual(session_data["variables"]["user"]["tier"], "vip")
        self.assertEqual(session_data["variables"]["channel"]["name"], "web")
        self.assertEqual(session_data["variables"]["global"]["locale"], "zh-CN")
        self.assertIsNotNone(session_data["expiresAt"])


def _start(client: TestClient, chatflow_id: int, stamp: int) -> dict[str, object]:
    response = client.post(
        f"/api/v1/chatflows/{chatflow_id}/runs-legacy",
        json={"input": {"sys.query": "start", "sys.conversation_id": f"conv-{stamp}"}},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "INTERRUPTED", data
    return data


def _create_variable_resume_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.3 Variable {stamp}",
            "description": "scoped variable fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "question_1", "type": "QUESTION", "name": "问题", "config": {"question": "主题？", "outputVariable": "answer"}},
                {
                    "nodeKey": "assign_1",
                    "type": "VARIABLE_ASSIGN",
                    "name": "变量赋值",
                    "config": {
                        "targetScope": "conversation",
                        "targetVariable": "topic",
                        "source": "{{question_1.answer}}",
                        "writeMode": "set",
                        "outputParameters": [{"name": "assigned", "type": "string"}],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "topic={{conversation.topic}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "assign_1", "condition": None},
                {"sourceNodeKey": "assign_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_message_chatflow(client: TestClient, stamp: int, content_template: str = "我叫 Ada，咨询 {{start.sys.query}}") -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.3 History {stamp}",
            "description": "history source fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "message_1", "type": "MESSAGE", "name": "消息", "config": {"content": content_template, "outputVariable": "content"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{message_1.content}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_scope_input_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.3 Scope Inputs {stamp}",
            "description": "scope input fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "{{sys.query}}|{{user.tier}}|{{channel.name}}|{{global.locale}}|{{start.externalId}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _replace_with_history_collection_chatflow(client: TestClient, chatflow_id: int, stamp: int, history_retention_rounds: int = 10) -> None:
    response = client.put(
        f"/api/v1/chatflows/{chatflow_id}",
        json={
            "name": f"018.3 History {stamp}",
            "description": "history collection fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {"historyRetentionRounds": history_retention_rounds}},
                {
                    "nodeKey": "collect_1",
                    "type": "INFORMATION_COLLECTION",
                    "name": "信息收集",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "collected",
                        "includeHistory": True,
                        "maxRounds": 1,
                        "fields": [
                            {"name": "name", "type": "string", "required": True, "description": "姓名"},
                            {"name": "phone", "type": "string", "required": True, "description": "手机号"},
                        ],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{collect_1.name}}|{{collect_1.phone}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "collect_1", "condition": None},
                {"sourceNodeKey": "collect_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text


if __name__ == "__main__":
    unittest.main()
