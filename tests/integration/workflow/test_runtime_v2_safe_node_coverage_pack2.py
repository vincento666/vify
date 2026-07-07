import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app
from app.modules.workflow.domain.runtime_v2 import RuntimeV2CompatibilityChecker


class RuntimeV2SafeNodeCoveragePack2Test(unittest.TestCase):
    def test_execute_workflow_node_invokes_published_child_workflow(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            child = _create_child_workflow(client, stamp)
            chatflow = _create_execute_workflow_chatflow(client, int(child["id"]))
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"ticket": "A-122", "sys.query": "please route ticket"}},
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"], {"final": "parent received child handled A-122"})
        execute_node = next(node for node in nodes if node["nodeKey"] == "execute_workflow_1")
        self.assertEqual(execute_node["status"], "COMPLETED")
        self.assertEqual(execute_node["outputs"]["childSummary"], "child handled A-122")
        self.assertEqual(execute_node["outputs"]["status"], "SUCCEEDED")
        self.assertGreater(execute_node["outputs"]["nestedRunId"], 0)
        self.assertNotIn("mocked", execute_node["outputs"])
        self.assertEqual(execute_node["outputs"]["mappedInputSummary"], {"ticket": "A-122"})
        self.assertEqual(execute_node["outputs"]["mappedOutputSummary"], {"childSummary": "child handled A-122"})
        completed_event = next(
            event
            for event in events
            if event["type"] == "workflow_node_completed" and event["nodeId"] == "execute_workflow_1"
        )
        self.assertEqual(completed_event["payload"]["nodeType"], "EXECUTE_WORKFLOW")
        self.assertGreater(completed_event["payload"]["output"]["nestedRunId"], 0)

    def test_transfer_to_human_waits_resumes_and_cancels_with_checkpoint_evidence(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_transfer_to_human_chatflow(client, stamp)
            resume_started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "我要人工",
                        "sys.conversation_id": f"handoff-resume-{stamp}",
                        "sys.user_id": "user-122",
                        "sys.channel": "web",
                    }
                },
            ).json()["data"]
            interrupted = _wait_for_result(client, resume_started["resultRef"], "INTERRUPTED")
            nodes_before_resume = client.get(resume_started["nodesRef"]).json()["data"]["list"]
            events_before_resume = client.get(resume_started["eventsRef"]).json()["data"]["list"]
            resumed_response = client.post(
                f"/api/v1/runtime-runs/{resume_started['runId']}/resume",
                json={
                    "resumeData": {"answer": "human accepted", "handoff_status": "resolved"},
                    "idempotencyKey": f"handoff-resume-{stamp}",
                },
            )

            cancel_started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {
                        "sys.query": "还要人工",
                        "sys.conversation_id": f"handoff-cancel-{stamp}",
                        "sys.user_id": "user-122",
                        "sys.channel": "web",
                    }
                },
            ).json()["data"]
            cancel_interrupted = _wait_for_result(client, cancel_started["resultRef"], "INTERRUPTED")
            cancelled_response = client.post(f"/api/v1/runtime-runs/{cancel_started['runId']}/cancel")

        self.assertEqual(interrupted["status"], "INTERRUPTED")
        assert interrupted["checkpoint"] is not None
        self.assertEqual(interrupted["checkpoint"]["pendingNodeKey"], "handoff_1")
        self.assertEqual(interrupted["checkpoint"]["resumeSchema"]["type"], "TRANSFER_TO_HUMAN")
        self.assertEqual(interrupted["checkpoint"]["resumeSchema"]["queue"], "vip-support")
        waiting_node = next(node for node in nodes_before_resume if node["nodeKey"] == "handoff_1")
        self.assertEqual(waiting_node["nodeType"], "TRANSFER_TO_HUMAN")
        self.assertEqual(waiting_node["status"], "WAITING")
        self.assertTrue(
            any(event["type"] == "handoff_requested" and event["nodeId"] == "handoff_1" for event in events_before_resume),
            events_before_resume,
        )

        self.assertEqual(resumed_response.status_code, 200, resumed_response.text)
        resumed = resumed_response.json()["data"]
        self.assertEqual(resumed["status"], "SUCCEEDED")
        self.assertEqual(resumed["checkpoint"], None)
        self.assertEqual(resumed["output"], {"final": "handoff=resolved answer=human accepted"})

        assert cancel_interrupted["checkpoint"] is not None
        cancelled = cancelled_response.json()["data"]
        self.assertEqual(cancelled_response.status_code, 200, cancelled_response.text)
        self.assertEqual(cancelled["status"], "CANCELLED")
        self.assertEqual(cancelled["checkpoint"], None)
        self.assertEqual(cancelled["cancellation"]["previousStatus"], "INTERRUPTED")

    def test_code_node_runs_in_runtime_v2_without_legacy_fallback(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_code_chatflow(client, stamp)
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={"input": {"sys.query": "Ada"}},
            )
            self.assertEqual(started_response.status_code, 200, started_response.text)
            started = started_response.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"], "SUCCEEDED")
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"], {"final": f"CODE_OK_{stamp}_Ada"})
        self.assertEqual([node["nodeKey"] for node in nodes], ["code_1", "end"])
        code_node = nodes[0]
        self.assertEqual(code_node["nodeType"], "CODE")
        self.assertEqual(code_node["outputs"]["computed"], f"CODE_OK_{stamp}_Ada")

    def test_runtime_v2_compatibility_allows_pack2_nodes_without_opening_unknown_nodes(self) -> None:
        supported = RuntimeV2CompatibilityChecker.check(
            [
                {"nodeKey": "start", "type": "START", "config": {}},
                {"nodeKey": "exec_1", "type": "EXECUTE_WORKFLOW", "config": {}},
                {"nodeKey": "llm_1", "type": "LLM", "config": {"prompt": "summarize"}},
                {"nodeKey": "code_1", "type": "CODE", "config": {"code": "result = {'output': 'ok'}"}},
                {"nodeKey": "handoff_1", "type": "TRANSFER_TO_HUMAN", "config": {}},
                {"nodeKey": "end", "type": "END", "config": {}},
            ],
            [
                {"sourceNodeKey": "start", "targetNodeKey": "exec_1"},
                {"sourceNodeKey": "exec_1", "targetNodeKey": "llm_1"},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "code_1"},
                {"sourceNodeKey": "code_1", "targetNodeKey": "handoff_1"},
                {"sourceNodeKey": "handoff_1", "targetNodeKey": "end"},
            ],
        )
        rejected = RuntimeV2CompatibilityChecker.check(
            [
                {"nodeKey": "start", "type": "START", "config": {}},
                {"nodeKey": "tool_1", "type": "TOOL_CALL", "config": {}},
            ],
            [{"sourceNodeKey": "start", "targetNodeKey": "tool_1"}],
        )

        self.assertTrue(supported["supported"], supported)
        self.assertIn("EXECUTE_WORKFLOW", supported["supportedNodeTypes"])
        self.assertIn("LLM", supported["supportedNodeTypes"])
        self.assertIn("CODE", supported["supportedNodeTypes"])
        self.assertIn("TRANSFER_TO_HUMAN", supported["supportedNodeTypes"])
        self.assertFalse(rejected["supported"])
        self.assertEqual(rejected["unsupportedNodes"][0]["nodeType"], "TOOL_CALL")


def _create_child_workflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/workflows",
        json={
            "name": f"Runtime V2 Pack 2 Child {stamp}",
            "description": "runtime v2 execute workflow child fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "format_1",
                    "type": "TEXT_PROCESS",
                    "name": "Format",
                    "config": {
                        "operation": "format_template",
                        "template": "child handled {{start.ticket}}",
                        "outputParameters": [{"name": "summary", "type": "string"}],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "summary", "output": "{{format_1.summary}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "format_1", "condition": None},
                {"sourceNodeKey": "format_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    child = response.json()["data"]
    update = client.put(
        f"/api/v1/workflows/{child['id']}",
        json={
            "name": child["name"],
            "description": child["description"],
            "status": "PUBLISHED",
            "nodes": child["nodes"],
            "edges": child["edges"],
        },
    )
    assert update.status_code == 200, update.text
    return update.json()["data"]


def _create_execute_workflow_chatflow(client: TestClient, target_workflow_id: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Pack 2 Execute Workflow {datetime.now().timestamp()}",
            "description": "runtime v2 safe execute workflow fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "execute_workflow_1",
                    "type": "EXECUTE_WORKFLOW",
                    "name": "Call Child",
                    "config": {
                        "targetWorkflowId": target_workflow_id,
                        "inputMappings": [
                            {"name": "ticket", "valueMode": "reference", "value": "{{start.ticket}}", "required": True},
                        ],
                        "outputMappings": [{"source": "summary", "target": "childSummary"}],
                        "outputParameters": [
                            {"name": "childSummary", "type": "string"},
                            {"name": "nestedRunId", "type": "number"},
                            {"name": "status", "type": "string"},
                            {"name": "mappedInputSummary", "type": "object"},
                            {"name": "mappedOutputSummary", "type": "object"},
                        ],
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "parent received {{execute_workflow_1.childSummary}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "execute_workflow_1", "condition": None},
                {"sourceNodeKey": "execute_workflow_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_code_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Pack 2 Code {stamp}",
            "description": "runtime v2 code fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "code_1",
                    "type": "CODE",
                    "name": "Code",
                    "config": {
                        "language": "python",
                        "code": f"result = {{'computed': 'CODE_OK_{stamp}_' + str(inputs.get('sys.query', ''))}}",
                        "outputParameters": [{"name": "computed", "type": "string"}],
                    },
                },
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "final", "output": "{{code_1.computed}}"}},
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "code_1", "condition": None},
                {"sourceNodeKey": "code_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_transfer_to_human_chatflow(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Pack 2 Handoff {stamp}",
            "description": "runtime v2 safe transfer fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "handoff_1",
                    "type": "TRANSFER_TO_HUMAN",
                    "name": "Transfer",
                    "config": {
                        "message": "已为你转接人工客服，请稍候。",
                        "queue": "vip-support",
                        "reason": "user_request",
                        "priority": "high",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "handoff={{handoff_1.handoff_status}} answer={{handoff_1.answer}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
                {"sourceNodeKey": "handoff_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str,
    timeout: float = 5.0,
) -> dict[str, object]:
    deadline = time.monotonic() + timeout
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        latest = client.get(result_ref).json()["data"]
        if latest["status"] == wanted_status:
            return latest
        time.sleep(0.1)
    raise AssertionError(f"Timed out waiting for {wanted_status}; latest={latest}")


if __name__ == "__main__":
    unittest.main()
