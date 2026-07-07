from __future__ import annotations

import unittest

from app.modules.runtime.domain.dag_selection import build_runtime_dag_selection_graph


class RuntimeDagSkippedJoinContractTest(unittest.TestCase):
    def test_skipped_upstream_does_not_block_implicit_join_waiting_state(self) -> None:
        states = _states_by_key(
            build_runtime_dag_selection_graph(
                nodes=[
                    {"nodeKey": "start", "type": "START"},
                    {"nodeKey": "router", "type": "CONDITION"},
                    {"nodeKey": "answer", "type": "MESSAGE"},
                    {"nodeKey": "fallback", "type": "MESSAGE"},
                    {"nodeKey": "join", "type": "HUMAN_INPUT"},
                    {"nodeKey": "end", "type": "END"},
                ],
                edges=[
                    {"sourceNodeKey": "start", "targetNodeKey": "router"},
                    {"sourceNodeKey": "router", "targetNodeKey": "answer", "condition": "matched"},
                    {"sourceNodeKey": "router", "targetNodeKey": "fallback"},
                    {"sourceNodeKey": "answer", "targetNodeKey": "join"},
                    {"sourceNodeKey": "fallback", "targetNodeKey": "join"},
                    {"sourceNodeKey": "join", "targetNodeKey": "end"},
                ],
                selected_ports={"router": ["matched"]},
                waiting_node_keys={"join"},
            )
        )

        self.assertEqual(states["answer"]["state"], "selected")
        self.assertEqual(states["fallback"]["state"], "skipped")
        self.assertEqual(states["join"]["state"], "waiting")
        self.assertEqual(states["join"]["selectedUpstreamNodeKeys"], ["answer"])
        self.assertEqual(states["join"]["skippedUpstreamNodeKeys"], ["fallback"])


def _states_by_key(states: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(state["nodeKey"]): state for state in states}


if __name__ == "__main__":
    unittest.main()
