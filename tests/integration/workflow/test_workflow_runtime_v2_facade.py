import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.workflow.domain.runtime_v2 import WorkflowRuntimeV2Service
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.publish_repository import WorkflowPublishRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class WorkflowRuntimeV2FacadeTest(unittest.TestCase):
    def test_workflow_v2_run_uses_published_snapshot_and_preserves_caller_context(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="published")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            first = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={
                    "input": {
                        "sys.query": "pricing",
                        "callerContext": {"router": "sop", "traceId": "wf-v2-ctx"},
                    },
                    "idempotencyKey": "workflow-v2-idempotent-1",
                },
            )
            duplicate = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={
                    "input": {
                        "sys.query": "pricing",
                        "callerContext": {"router": "sop", "traceId": "wf-v2-ctx"},
                    },
                    "idempotencyKey": "workflow-v2-idempotent-1",
                },
            )
            _replace_workflow_message(client, workflow["id"], message="draft-edited")
            started = first.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            observe_detail = client.get(f"/api/v1/observe/runs/{started['runId']}").json()["data"]
            debug = client.get(f"/api/v1/workflows/{workflow['id']}/runs/{started['runId']}/debug").json()["data"]

        self.assertEqual(first.status_code, 200, first.text)
        self.assertEqual(duplicate.status_code, 200, duplicate.text)
        self.assertFalse(started["idempotentReplay"])
        self.assertTrue(duplicate.json()["data"]["idempotentReplay"])
        self.assertEqual(started["runId"], duplicate.json()["data"]["runId"])
        self.assertEqual(started["ownerType"], "WORKFLOW")
        self.assertEqual(started["ownerId"], workflow["id"])
        self.assertEqual(started["workflowId"], workflow["id"])
        self.assertEqual(started["versionId"], version["id"])
        self.assertEqual(started["version"], version["version"])
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "published"})
        self.assertTrue(any(event["payload"]["callerContext"]["traceId"] == "wf-v2-ctx" for event in events))
        self.assertEqual(observe_detail["sessionId"], "")
        self.assertEqual(debug["ownerType"], "WORKFLOW")
        self.assertEqual([node["status"] for node in debug["nodeDetails"]], ["SUCCEEDED", "SUCCEEDED"])
        self.assertTrue(any(event["type"] == "workflow_node_completed" for event in debug["events"]))

    def test_workflow_v2_executes_llm_node_with_runtime_events(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="unsupported", node_type="LLM")
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "hello runtime v2 llm"}},
            ).json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "LLM mock: unsupported"})
        self.assertTrue(
            any(
                event["type"] == "workflow_node_completed"
                and event.get("nodeId") == "middle_1"
                and event["payload"]["nodeType"] == "LLM"
                for event in events
            ),
            events,
        )
        llm_node = next(node for node in nodes if node["nodeKey"] == "middle_1")
        self.assertEqual(llm_node["status"], "COMPLETED")
        self.assertEqual(llm_node["outputs"]["content"], "LLM mock: unsupported")

    def test_workflow_v2_rejects_unsupported_graph_without_partial_execution(self) -> None:
        with TestClient(app) as client:
            workflow = _create_branching_message_workflow(client)
            published = client.post(f"/api/v1/workflows/{workflow['id']}/publish")
            self.assertEqual(published.status_code, 200, published.text)
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "hello"}},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("unsupportedPatterns", payload["message"])
        self.assertNotIn("eventStreamRef", payload)

    def test_workflow_v2_resume_uses_published_snapshot_after_draft_edit(self) -> None:
        with TestClient(app) as client:
            workflow = _create_question_message_workflow(client, message="published")
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "refund"}},
            ).json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"])
            _replace_question_message_workflow_message(client, workflow["id"], message="draft-edited")
            resumed = client.post(
                f"/api/v1/runtime-runs/{started['runId']}/resume",
                json={"resumeData": {"answer": "yes"}, "idempotencyKey": "workflow-v2-snapshot-resume-1"},
            )

        self.assertEqual(interrupted["status"], "INTERRUPTED")
        self.assertEqual(resumed.status_code, 200, resumed.text)
        data = resumed.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "published answer=yes"})
        self.assertEqual(data["versionId"], version["id"])
        self.assertEqual(data["version"], version["version"])

    def test_workflow_v2_knowledge_uses_published_snapshot_and_real_faq_answer(self) -> None:
        with TestClient(app) as client:
            kb_id = _create_knowledge_base_with_faq(client)
            workflow = _create_knowledge_workflow(client, kb_id)
            version = client.post(f"/api/v1/workflows/{workflow['id']}/publish").json()["data"]
            _replace_workflow_message(client, workflow["id"], message="draft-edited")
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs-v2",
                json={"input": {"sys.query": "workflow v2 refund knowledge"}},
            ).json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"]["answer"], "Workflow v2 published FAQ answer.")
        self.assertNotIn("Knowledge mock:", str(terminal))
        self.assertEqual(terminal["versionId"], version["id"])
        self.assertEqual(terminal["version"], version["version"])
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

    def test_workflow_v2_knowledge_without_facade_fails_explicitly_not_mock(self) -> None:
        with TestClient(app) as client:
            kb_id = _create_knowledge_base_with_faq(client)
            workflow = _create_knowledge_workflow(client, kb_id)
            client.post(f"/api/v1/workflows/{workflow['id']}/publish")

        with get_session_factory()() as session:
            service = WorkflowRuntimeV2Service(
                WorkflowRepository(session),
                ChatflowStateRepository(session),
                WorkflowPublishRepository(session),
                completion_delay_seconds=0,
                knowledge_facade=None,
            )
            started = service.start_run(int(workflow["id"]), {"sys.query": "workflow v2 refund knowledge"})
            service.complete_run(int(started["runId"]))
            result = service.get_result(int(started["runId"]))

        self.assertEqual(result["status"], "FAILED")
        self.assertIn("requires KnowledgeFacade", result["error"])
        self.assertNotIn("Knowledge mock:", str(result))

    def test_legacy_workflow_run_response_stays_compatible(self) -> None:
        with TestClient(app) as client:
            workflow = _create_workflow(client, message="legacy")
            response = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "hello"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "legacy"})
        self.assertIn("debugUrl", data)


def _wait_for_result(client: TestClient, result_ref: str, timeout: float = 5.0) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] in {"SUCCEEDED", "FAILED", "INTERRUPTED"}:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for terminal result; latest={latest}")


def _create_workflow(client: TestClient, *, message: str, node_type: str = "MESSAGE") -> dict[str, object]:
    middle_config = {"content": message, "outputVariable": "content"}
    if node_type == "LLM":
        middle_config = {"prompt": message, "outputVariable": "content"}
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow V2 Facade {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "middle_1", "type": node_type, "name": "Middle", "config": middle_config},
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{middle_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "middle_1", "condition": None},
                {"sourceNodeKey": "middle_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_branching_message_workflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow V2 Branching Unsupported {datetime.now().timestamp()}",
            "description": "runtime v2 rejects non-condition branching before partial execution",
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


def _create_question_message_workflow(client: TestClient, *, message: str) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow V2 Resume Snapshot {datetime.now().timestamp()}",
            "description": "",
            "nodes": _question_message_nodes(message),
            "edges": _question_message_edges(),
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_knowledge_base_with_faq(client: TestClient) -> int:
    created = client.post(
        "/api/v1/knowledge-bases",
        json={"name": f"Workflow V2 Knowledge KB {time.time_ns()}", "description": "workflow v2 knowledge fixture"},
    )
    assert created.status_code == 200, created.text
    kb_id = int(created.json()["data"]["id"])
    faq = client.post(
        f"/api/v1/knowledge-bases/{kb_id}/faqs",
        json={
            "question": "How does workflow v2 answer published knowledge?",
            "answer": "Workflow v2 published FAQ answer.",
            "alternativeQuestions": ["workflow v2 refund knowledge"],
            "keywords": ["refund", "workflow", "knowledge"],
            "category": "workflow-v2",
            "priority": 20,
            "enabled": True,
            "metadata": {},
            "source": "test",
        },
    )
    assert faq.status_code == 200, faq.text
    return kb_id


def _create_knowledge_workflow(client: TestClient, kb_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Workflow V2 Knowledge {time.time_ns()}",
            "description": "published runtime v2 knowledge fixture",
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


def _replace_workflow_message(client: TestClient, workflow_id: int, *, message: str) -> None:
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "middle_1",
                    "type": "MESSAGE",
                    "name": "Middle",
                    "config": {"content": message, "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{middle_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "middle_1", "condition": None},
                {"sourceNodeKey": "middle_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text


def _replace_question_message_workflow_message(client: TestClient, workflow_id: int, *, message: str) -> None:
    response = client.put(
        f"/api/v1/workflows/{workflow_id}",
        json={
            "nodes": _question_message_nodes(message),
            "edges": _question_message_edges(),
        },
    )
    assert response.status_code == 200, response.text


def _question_message_nodes(message: str) -> list[dict[str, object]]:
    return [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "question_1",
            "type": "QUESTION",
            "name": "Question",
            "config": {"question": "Continue?", "outputVariable": "answer", "answerType": "text"},
        },
        {
            "nodeKey": "message_1",
            "type": "MESSAGE",
            "name": "Message",
            "config": {"content": f"{message} answer={{{{question_1.answer}}}}", "outputVariable": "content"},
        },
        {
            "nodeKey": "end",
            "type": "END",
            "name": "End",
            "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
        },
    ]


def _question_message_edges() -> list[dict[str, object]]:
    return [
        {"sourceNodeKey": "start", "targetNodeKey": "question_1", "condition": None},
        {"sourceNodeKey": "question_1", "targetNodeKey": "message_1", "condition": None},
        {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
    ]


if __name__ == "__main__":
    unittest.main()
