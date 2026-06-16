import time
import unittest

from fastapi.testclient import TestClient
import sqlalchemy as sa

from app.core.database import Base, get_session_factory
from app.main import app


class ChatflowResumeApiIntegrationTest(unittest.TestCase):
    def test_question_resume_continues_same_run_from_checkpoint(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp)
            run_id = int(interrupted["runId"])
            event_id = int(interrupted["events"][-1]["id"])
            resumed_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"answer": "yes"}},
            )
            events_response = client.get(f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/events")

        self.assertEqual(resumed_response.status_code, 200, resumed_response.text)
        resumed = resumed_response.json()["data"]
        self.assertEqual(resumed["runId"], run_id)
        self.assertEqual(resumed["status"], "SUCCEEDED")
        self.assertEqual(resumed["output"], {"final": "answer=yes"})
        self.assertEqual(_run_status(run_id), "SUCCEEDED")
        self.assertEqual([event["type"] for event in events_response.json()["data"]["list"]], ["message", "interrupt", "resume", "done"])

    def test_human_input_resume_continues_same_run_from_payload(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_human_input_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp)
            run_id = int(interrupted["runId"])
            event_id = int(interrupted["events"][-1]["id"])
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"payload": {"approved": True, "note": "ok"}}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["runId"], run_id)
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "approved=True note=ok"})

    def test_information_collection_resume_merges_checkpoint_state(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client, stamp)
            interrupted = _start(client, int(chatflow["id"]), stamp, query="我叫 Ada")
            run_id = int(interrupted["runId"])
            event_id = int(interrupted["events"][-1]["id"])
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs/{run_id}/resume",
                json={"eventId": event_id, "resumeData": {"answer": "手机号 13800138000"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["runId"], run_id)
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "Ada|13800138000|Ada"})


def _start(client: TestClient, chatflow_id: int, stamp: int, query: str = "start") -> dict[str, object]:
    response = client.post(
        f"/api/v1/chatflows/{chatflow_id}/runs",
        json={
            "input": {
                "sys.query": query,
                "sys.conversation_id": f"conv-{stamp}",
                "sys.user_id": "user-018",
                "sys.channel": "web",
            }
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert data["status"] == "INTERRUPTED", data
    return data


def _create_question_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.2 Question {stamp}",
            "description": "resume question fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "question_1", "type": "QUESTION", "name": "问题", "config": {"question": "继续吗？", "outputVariable": "answer"}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "answer={{question_1.answer}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_human_input_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.2 Human {stamp}",
            "description": "resume human fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "human_input_1", "type": "HUMAN_INPUT", "name": "人工输入", "config": {"prompt": "请审核", "outputVariable": "payload"}},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "approved={{human_input_1.approved}} note={{human_input_1.note}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "human_input_1", "condition": None},
                {"sourceNodeKey": "human_input_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_information_collection_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"018.2 Info {stamp}",
            "description": "resume info fixture",
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
                        "fields": [
                            {"name": "name", "type": "string", "required": True, "description": "姓名", "targetScope": "conversation", "targetVariable": "customer_name"},
                            {"name": "phone", "type": "string", "required": True, "description": "手机号"},
                        ],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{info_1.name}}|{{info_1.phone}}|{{conversation.customer_name}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_1", "condition": None},
                {"sourceNodeKey": "info_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _run_status(run_id: int) -> str:
    workflow_run = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        return str(session.execute(sa.select(workflow_run.c.status).where(workflow_run.c.id == run_id)).scalar_one())


if __name__ == "__main__":
    unittest.main()
