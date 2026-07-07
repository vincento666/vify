from __future__ import annotations

import unittest

from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.runtime.domain.dag_selection import build_runtime_dag_selection_graph

register_baseline_tables()


class RuntimeDagBranchMultiTargetContractTest(unittest.TestCase):
    def test_runtime_node_run_exposes_selection_state_column(self) -> None:
        table = Base.metadata.tables["workflow_node_run"]

        self.assertIn("selection_state", table.c)

    def test_selected_branch_port_marks_all_targets_selected_and_other_ports_skipped(self) -> None:
        states = _states_by_key(
            build_runtime_dag_selection_graph(
                nodes=[
                    {"nodeKey": "start", "type": "START"},
                    {"nodeKey": "router", "type": "CONDITION"},
                    {"nodeKey": "vip_a", "type": "MESSAGE"},
                    {"nodeKey": "vip_b", "type": "MESSAGE"},
                    {"nodeKey": "fallback", "type": "MESSAGE"},
                    {"nodeKey": "join", "type": "VARIABLE_AGGREGATION"},
                    {"nodeKey": "end", "type": "END"},
                ],
                edges=[
                    {"sourceNodeKey": "start", "targetNodeKey": "router"},
                    {"sourceNodeKey": "router", "targetNodeKey": "vip_a", "condition": "vip"},
                    {"sourceNodeKey": "router", "targetNodeKey": "vip_b", "sourcePortKey": "vip"},
                    {"sourceNodeKey": "router", "targetNodeKey": "fallback"},
                    {"sourceNodeKey": "vip_a", "targetNodeKey": "join"},
                    {"sourceNodeKey": "vip_b", "targetNodeKey": "join"},
                    {"sourceNodeKey": "fallback", "targetNodeKey": "join"},
                    {"sourceNodeKey": "join", "targetNodeKey": "end"},
                ],
                selected_ports={"router": ["vip"]},
            )
        )

        self.assertEqual(states["vip_a"]["state"], "selected")
        self.assertEqual(states["vip_b"]["state"], "selected")
        self.assertEqual(states["fallback"]["state"], "skipped")
        self.assertEqual(states["join"]["state"], "pending")
        self.assertEqual(states["join"]["selectedUpstreamNodeKeys"], ["vip_a", "vip_b"])
        self.assertEqual(states["join"]["skippedUpstreamNodeKeys"], ["fallback"])


def _states_by_key(states: list[dict[str, object]]) -> dict[str, dict[str, object]]:
    return {str(state["nodeKey"]): state for state in states}


if __name__ == "__main__":
    unittest.main()
