import unittest
from datetime import datetime
import time

from fastapi.testclient import TestClient

from app.main import app


class ChatflowRuntimeV2FacadeTest(unittest.TestCase):
    def test_knowledge_node_returns_faq_answer_and_runtime_node_evidence(self) -> None:
        with TestClient(app) as client:
            kb_id = _create_knowledge_base_with_faq(client)
            chatflow = _create_knowledge_chatflow(client, kb_id)
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "runtime v2 refund knowledge",
                        "sys.conversation_id": f"knowledge-v2-{time.time_ns()}",
                        "sys.user_id": "user-runtime-v2-knowledge",
                        "sys.channel": "web",
                    }
                },
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["answer"], "Runtime v2 knowledge FAQ answer.")
        self.assertEqual(terminal["sessionId"], started["sessionId"])
        self.assertTrue(
            any(
                event["type"] == "workflow_node_completed"
                and event.get("nodeId") == "knowledge_1"
                and event["payload"]["nodeType"] == "KNOWLEDGE"
                for event in events
            ),
            events,
        )
        knowledge_node = next(node for node in nodes if node["nodeKey"] == "knowledge_1")
        self.assertEqual(knowledge_node["status"], "COMPLETED")

    def test_unsupported_chatflow_graph_is_rejected_without_live_v2_refs(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_unsupported_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "Ada"}},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertEqual(payload["code"], 400)
        self.assertIn("Runtime V2 graph is not compatible", payload["message"])
        self.assertIn("default outlet must enable fan-out", payload["message"])
        self.assertNotIn("eventStreamRef", payload)

    def test_resume_is_idempotent_for_same_checkpoint_and_input(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_question_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "start"}},
            ).json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"], "INTERRUPTED")
            first_resume = client.post(
                f"/api/v1/runtime-runs/{started['runId']}/resume",
                json={"resumeData": {"answer": "yes"}, "idempotencyKey": "resume-1"},
            )
            second_resume = client.post(
                f"/api/v1/runtime-runs/{started['runId']}/resume",
                json={"resumeData": {"answer": "yes"}, "idempotencyKey": "resume-1"},
            )
            events = client.get(started["eventsRef"]).json()["data"]["list"]

        self.assertEqual(interrupted["status"], "INTERRUPTED")
        self.assertEqual(first_resume.status_code, 200)
        self.assertEqual(second_resume.status_code, 200)
        self.assertEqual(first_resume.json()["data"]["output"], second_resume.json()["data"]["output"])
        self.assertEqual([event["type"] for event in events].count("workflow_run_completed"), 1)


def _create_unsupported_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow V2 Facade Unsupported {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_a",
                    "type": "MESSAGE",
                    "name": "Message A",
                    "config": {"content": "branch a", "outputVariable": "content"},
                },
                {
                    "nodeKey": "message_b",
                    "type": "MESSAGE",
                    "name": "Message B",
                    "config": {"content": "branch b", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_a.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_a", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "message_b", "condition": None},
                {"sourceNodeKey": "message_a", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "message_b", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_knowledge_base_with_faq(client: TestClient) -> int:
    created = client.post(
        "/api/v1/knowledge-bases",
        json={"name": f"Runtime V2 Knowledge KB {time.time_ns()}", "description": "runtime v2 knowledge fixture"},
    )
    assert created.status_code == 200, created.text
    kb_id = int(created.json()["data"]["id"])
    faq = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/faqs",
        json={
            "question": "How does runtime v2 answer refund knowledge?",
            "answer": "Runtime v2 knowledge FAQ answer.",
            "alternativeQuestions": ["runtime v2 refund knowledge"],
            "keywords": ["refund", "runtime", "knowledge"],
            "category": "runtime-v2",
            "priority": 20,
            "enabled": True,
            "metadata": {},
            "source": "test",
        },
    )
    assert faq.status_code == 200, faq.text
    return kb_id


def _create_knowledge_chatflow(client: TestClient, kb_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow V2 Knowledge {time.time_ns()}",
            "description": "runtime v2 knowledge tracer bullet",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "knowledge_1",
                    "type": "KNOWLEDGE",
                    "name": "Knowledge",
                    "config": {
                        "knowledgeBaseId": kb_id,
                        "query": "{{start.sys.query}}",
                        "topK": 3,
                        "retrievalMode": "faq",
                        "outputVariable": "answer",
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "knowledge_1", "condition": None},
                {"sourceNodeKey": "knowledge_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_result(client: TestClient, result_ref: str, wanted_status: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


def _create_question_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow V2 Facade Question {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "question_1",
                    "type": "QUESTION",
                    "name": "Question",
                    "config": {"question": "Continue?", "outputVariable": "answer", "answerType": "text"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "answer={{question_1.answer}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
                {"sourceNodeKey": "question_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
