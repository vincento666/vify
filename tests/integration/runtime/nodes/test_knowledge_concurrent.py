from __future__ import annotations

import time
import unittest

from fastapi.testclient import TestClient

from app.main import app

from ._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2KnowledgeConcurrentTest(unittest.TestCase):
    def test_three_knowledge_nodes_in_same_frontier_wave_keep_outputs_and_events_isolated(self) -> None:
        node_keys = {"knowledge_a", "knowledge_b", "knowledge_c"}
        with TestClient(app) as client:
            kb_id = _create_knowledge_base_with_faq_matrix(client)
            workflow = create_fanout_workflow(
                client,
                name_prefix="217.2 Knowledge fanout",
                nodes=[
                    _knowledge_node("knowledge_a", kb_id, "alpha policy", "answer_a"),
                    _knowledge_node("knowledge_b", kb_id, "beta policy", "answer_b"),
                    _knowledge_node("knowledge_c", kb_id, "gamma policy", "answer_c"),
                ],
                output_template="{{knowledge_a.answer_a}}|{{knowledge_b.answer_b}}|{{knowledge_c.answer_c}}",
            )
            started = client.post(
                f"/api/v1/workflows/{workflow['id']}/runs",
                json={"input": {"sys.query": "knowledge wave"}},
            ).json()["data"]
            terminal = wait_for_runtime_result(client, started["resultRef"])
            events = client.get(started["eventsRef"]).json()["data"]["list"]
            nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["final"], "alpha answer|beta answer|gamma answer")
        assert_completed_node_runs(nodes, node_keys, "KNOWLEDGE")
        assert_wave_started_before_first_completion(events, node_keys)


def _create_knowledge_base_with_faq_matrix(client: TestClient) -> int:
    created = client.post(
        "/api/v1/knowledge-bases",
        json={"name": f"217.2 Knowledge KB {time.time_ns()}", "description": "node concurrency fixture"},
    )
    assert created.status_code == 200, created.text
    kb_id = int(created.json()["data"]["id"])
    for question, answer, keywords in [
        ("alpha policy", "alpha answer", ["alpha", "policy"]),
        ("beta policy", "beta answer", ["beta", "policy"]),
        ("gamma policy", "gamma answer", ["gamma", "policy"]),
    ]:
        faq = client.post(
            f"/api/v1/knowledge-bases/{kb_id}/faqs",
            json={
                "question": question,
                "answer": answer,
                "alternativeQuestions": [question],
                "keywords": keywords,
                "category": "217.2",
                "priority": 20,
                "enabled": True,
                "metadata": {},
                "source": "test",
            },
        )
        assert faq.status_code == 200, faq.text
    return kb_id


def _knowledge_node(node_key: str, kb_id: int, query: str, output_variable: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "KNOWLEDGE",
        "name": node_key,
        "config": {
            "knowledgeBaseId": kb_id,
            "query": query,
            "topK": 1,
            "retrievalMode": "faq",
            "outputVariable": output_variable,
        },
    }


if __name__ == "__main__":
    unittest.main()
