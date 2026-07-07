from __future__ import annotations

import unittest
from unittest.mock import patch

from fastapi.testclient import TestClient

from app.main import app

from ._helpers import (
    assert_completed_node_runs,
    assert_wave_started_before_first_completion,
    create_fanout_workflow,
    wait_for_runtime_result,
)


class RuntimeV2LlmConcurrentTest(unittest.TestCase):
    def test_three_llm_nodes_in_same_frontier_wave_keep_outputs_and_events_isolated(self) -> None:
        node_keys = {"llm_a", "llm_b", "llm_c"}
        with patch("app.modules.agent.infra.repository.AgentRepository.find_default_live_llm_agent", return_value=None):
            with TestClient(app) as client:
                workflow = create_fanout_workflow(
                    client,
                    name_prefix="217.2 LLM fanout",
                    nodes=[
                        _llm_node("llm_a", "A"),
                        _llm_node("llm_b", "B"),
                        _llm_node("llm_c", "C"),
                    ],
                    output_template="{{llm_a.answer}}|{{llm_b.answer}}|{{llm_c.answer}}",
                )
                started = client.post(
                    f"/api/v1/workflows/{workflow['id']}/runs",
                    json={"input": {"sys.query": "runtime wave"}},
                ).json()["data"]
                terminal = wait_for_runtime_result(client, started["resultRef"])
                events = client.get(started["eventsRef"]).json()["data"]["list"]
                nodes = client.get(started["nodesRef"]).json()["data"]["list"]

        self.assertEqual(terminal["output"]["final"], "LLM mock: prompt A runtime wave|LLM mock: prompt B runtime wave|LLM mock: prompt C runtime wave")
        assert_completed_node_runs(nodes, node_keys, "LLM")
        assert_wave_started_before_first_completion(events, node_keys)


def _llm_node(node_key: str, suffix: str) -> dict[str, object]:
    return {
        "nodeKey": node_key,
        "type": "LLM",
        "name": f"LLM {suffix}",
        "config": {"prompt": f"prompt {suffix} {{{{start.sys.query}}}}", "outputVariable": "answer"},
    }


if __name__ == "__main__":
    unittest.main()
