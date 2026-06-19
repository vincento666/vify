import time
import unittest
from datetime import datetime

from fastapi.testclient import TestClient

from app.main import app


class RuntimeV2NodeCoveragePack1Test(unittest.TestCase):
    def test_deterministic_transform_variable_nodes_run_in_v2(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_transform_variable_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"primary": "gold", "fallback": "standard", "sys.query": "  Ada  "}},
            )
            terminal = _wait_for_result(client, started.json()["data"]["resultRef"])
            nodes = client.get(started.json()["data"]["nodesRef"]).json()["data"]["list"]

        self.assertEqual(started.status_code, 200, started.text)
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "route=gold name=Ada"})
        self.assertEqual(
            [node["nodeType"] for node in nodes],
            ["TEXT_PROCESS", "JSON_PARSE", "VARIABLE_AGGREGATION", "VARIABLE_ASSIGN", "END"],
        )
        self.assertTrue(all(node["status"] == "COMPLETED" for node in nodes))

    def test_intent_and_condition_nodes_route_by_deterministic_branch(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_branch_chatflow(client)
            started_response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "I need pricing details"}},
            )
            started = started_response.json()["data"]
            terminal = _wait_for_result(client, started["resultRef"])
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(started_response.status_code, 200, started_response.text)
        self.assertEqual(terminal["status"], "SUCCEEDED")
        self.assertEqual(terminal["output"], {"final": "pricing"})
        self.assertEqual([node["nodeKey"] for node in nodes], ["intent_1", "condition_1", "price_msg", "end"])

    def test_information_collection_interrupts_and_resumes_with_followup_checkpoint(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client)
            started = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "我叫 Ada"}},
            ).json()["data"]
            interrupted = _wait_for_result(client, started["resultRef"], "INTERRUPTED")
            nodes_before_resume = client.get(started["nodesRef"]).json()["data"]["list"]
            resumed = client.post(
                f"/api/v1/runtime-runs/{started['runId']}/resume",
                json={"resumeData": {"answer": "手机号: 13800138000"}, "idempotencyKey": "info-resume-1"},
            )
            final = resumed.json()["data"]

        self.assertEqual(interrupted["status"], "INTERRUPTED")
        assert interrupted["checkpoint"] is not None
        self.assertEqual(interrupted["checkpoint"]["pendingNodeKey"], "collect_1")
        self.assertIn("手机号", interrupted["checkpoint"]["resumeSchema"]["followup"])
        self.assertEqual(nodes_before_resume[-1]["nodeType"], "INFORMATION_COLLECTION")
        self.assertEqual(nodes_before_resume[-1]["status"], "WAITING")
        self.assertEqual(resumed.status_code, 200, resumed.text)
        self.assertEqual(final["status"], "SUCCEEDED")
        self.assertEqual(final["output"], {"final": "name=Ada phone=13800138000"})

    def test_llm_dependent_information_collection_blocks_whole_graph_v2(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_information_collection_chatflow(client, extractor_mode="llm")
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-v2",
                json={"input": {"sys.query": "我叫 Ada"}},
            )

        self.assertEqual(response.status_code, 400)
        payload = response.json()
        self.assertIn("llm_dependent_information_collection", payload["message"])
        self.assertNotIn("eventStreamRef", payload)


def _wait_for_result(
    client: TestClient,
    result_ref: str,
    wanted_status: str = "SUCCEEDED",
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


def _create_transform_variable_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Coverage Pack 1 {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "trim_1",
                    "type": "TEXT_PROCESS",
                    "name": "Trim",
                    "config": {"operation": "trim", "source": "{{start.sys.query}}", "outputVariable": "name"},
                },
                {
                    "nodeKey": "json_1",
                    "type": "JSON_PARSE",
                    "name": "JSON",
                    "config": {"sourceValue": "{\"tier\":\"gold\"}", "outputVariable": "parsed"},
                },
                {
                    "nodeKey": "aggregate_1",
                    "type": "VARIABLE_AGGREGATION",
                    "name": "Aggregate",
                    "config": {
                        "strategy": "first_non_empty",
                        "sources": [
                            {"name": "primary", "value": "{{start.primary}}"},
                            {"name": "fallback", "value": "{{start.fallback}}"},
                        ],
                        "outputVariable": "selected",
                    },
                },
                {
                    "nodeKey": "assign_1",
                    "type": "VARIABLE_ASSIGN",
                    "name": "Assign",
                    "config": {
                        "targetScope": "flow",
                        "targetVariable": "route",
                        "source": "{{aggregate_1.selected}}",
                        "writeMode": "set",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "route={{flow.route}} name={{trim_1.name}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "trim_1", "condition": None},
                {"sourceNodeKey": "trim_1", "targetNodeKey": "json_1", "condition": None},
                {"sourceNodeKey": "json_1", "targetNodeKey": "aggregate_1", "condition": None},
                {"sourceNodeKey": "aggregate_1", "targetNodeKey": "assign_1", "condition": None},
                {"sourceNodeKey": "assign_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_branch_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Coverage Branch {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "intent_1",
                    "type": "INTENT_RECOGNITION",
                    "name": "Intent",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "intent",
                        "defaultIntent": "general",
                        "intents": [
                            {"key": "pricing", "name": "Pricing", "examples": ["pricing", "price"]},
                            {"key": "general", "name": "General", "examples": ["hello"]},
                        ],
                    },
                },
                {
                    "nodeKey": "condition_1",
                    "type": "CONDITION",
                    "name": "Condition",
                    "config": {
                        "outputVariable": "route",
                        "branches": [
                            {
                                "key": "pricing",
                                "conditions": [
                                    {"left": "{{intent_1.intent}}", "operator": "equals", "right": "pricing"}
                                ],
                            }
                        ],
                        "defaultBranch": "general",
                    },
                },
                {
                    "nodeKey": "price_msg",
                    "type": "MESSAGE",
                    "name": "Pricing Message",
                    "config": {"content": "pricing", "outputVariable": "content"},
                },
                {
                    "nodeKey": "general_msg",
                    "type": "MESSAGE",
                    "name": "General Message",
                    "config": {"content": "general", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{price_msg.content}}{{general_msg.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "intent_1", "condition": None},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "condition_1", "condition": "pricing"},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "general_msg", "condition": None},
                {"sourceNodeKey": "condition_1", "targetNodeKey": "price_msg", "condition": "pricing"},
                {"sourceNodeKey": "condition_1", "targetNodeKey": "general_msg", "condition": None},
                {"sourceNodeKey": "price_msg", "targetNodeKey": "end", "condition": None},
                {"sourceNodeKey": "general_msg", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


def _create_information_collection_chatflow(
    client: TestClient,
    *,
    extractor_mode: str = "fake",
) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime V2 Coverage Info Collection {datetime.now().timestamp()}",
            "description": "",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "collect_1",
                    "type": "INFORMATION_COLLECTION",
                    "name": "Collect",
                    "config": {
                        "extractorMode": extractor_mode,
                        "inputSource": "{{start.sys.query}}",
                        "followupTemplate": "请补充{{missing_labels}}",
                        "fields": [
                            {
                                "name": "name",
                                "description": "姓名",
                                "required": True,
                                "targetScope": "flow",
                                "targetVariable": "customerName",
                            },
                            {
                                "name": "phone",
                                "description": "手机号",
                                "required": True,
                                "targetScope": "flow",
                                "targetVariable": "customerPhone",
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
                        "output": "name={{flow.customerName}} phone={{flow.customerPhone}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "collect_1", "condition": None},
                {"sourceNodeKey": "collect_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
