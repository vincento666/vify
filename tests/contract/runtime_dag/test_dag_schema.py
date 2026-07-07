from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.modules.runtime.api.schemas import (
    BranchGroupSpec,
    EdgeSpec,
    FinalOutputRule,
    NodeSelectionState,
    PortSpec,
)
from app.modules.workflow.api.schemas import EdgeSpec as WorkflowEdgeSpec


class RuntimeDagSchemaContractTest(unittest.TestCase):
    def test_edge_spec_captures_source_port_target_and_branch_metadata(self) -> None:
        edge = EdgeSpec.model_validate(
            {
                "sourceNodeKey": "condition_1",
                "sourcePortKey": "vip",
                "targetNodeKey": "api_notify",
                "targetPortKey": "input",
                "branchGroupKey": "condition_1.outcome",
                "condition": "tier == 'vip'",
                "sideEffectTerminal": True,
            }
        )

        self.assertEqual(edge.source_node_key, "condition_1")
        self.assertEqual(edge.source_port_key, "vip")
        self.assertEqual(edge.target_node_key, "api_notify")
        self.assertEqual(edge.target_port_key, "input")
        self.assertEqual(edge.branch_group_key, "condition_1.outcome")
        self.assertTrue(edge.side_effect_terminal)
        self.assertEqual(
            edge.model_dump(by_alias=True, exclude_none=True),
            {
                "sourceNodeKey": "condition_1",
                "sourcePortKey": "vip",
                "targetNodeKey": "api_notify",
                "targetPortKey": "input",
                "branchGroupKey": "condition_1.outcome",
                "condition": "tier == 'vip'",
                "sideEffectTerminal": True,
            },
        )

    def test_port_and_branch_group_specs_make_fanout_explicit(self) -> None:
        port = PortSpec.model_validate(
            {
                "nodeKey": "condition_1",
                "portKey": "vip",
                "portType": "branch",
                "branchGroupKey": "condition_1.outcome",
                "allowFanOut": True,
            }
        )
        branch_group = BranchGroupSpec.model_validate(
            {
                "branchGroupKey": "condition_1.outcome",
                "nodeKey": "condition_1",
                "selectionMode": "single",
                "selectedPortKeys": ["vip"],
                "skippedPortKeys": ["default"],
            }
        )

        self.assertTrue(port.allow_fan_out)
        self.assertEqual(port.port_type, "branch")
        self.assertEqual(branch_group.selection_mode, "single")
        self.assertEqual(branch_group.selected_port_keys, ["vip"])
        self.assertEqual(branch_group.skipped_port_keys, ["default"])

    def test_node_selection_state_enumerates_selected_skipped_and_terminal_states(self) -> None:
        selected = NodeSelectionState.model_validate(
            {
                "nodeKey": "join_1",
                "state": "selected",
                "selectedUpstreamNodeKeys": ["branch_a"],
                "skippedUpstreamNodeKeys": ["branch_b"],
                "reason": "implicit join waits only for selected upstreams",
            }
        )

        self.assertEqual(selected.state, "selected")
        self.assertEqual(selected.selected_upstream_node_keys, ["branch_a"])
        self.assertEqual(selected.skipped_upstream_node_keys, ["branch_b"])

        for state in (
            "pending",
            "running",
            "waiting",
            "completed",
            "failed",
            "cancelled",
            "skipped",
        ):
            NodeSelectionState.model_validate({"nodeKey": f"node_{state}", "state": state})

        with self.assertRaises(ValidationError):
            NodeSelectionState.model_validate({"nodeKey": "bad", "state": "blocked"})

    def test_final_output_rule_distinguishes_chatflow_reply_from_workflow_side_effect_only(self) -> None:
        chatflow_rule = FinalOutputRule.model_validate(
            {
                "ownerType": "CHATFLOW",
                "strategy": "end_node_first",
                "requiresVisibleOutput": True,
                "allowsSideEffectOnly": False,
                "candidateNodeKeys": ["end", "answer_1"],
            }
        )
        workflow_rule = FinalOutputRule.model_validate(
            {
                "ownerType": "WORKFLOW",
                "strategy": "side_effect_summary",
                "requiresVisibleOutput": False,
                "allowsSideEffectOnly": True,
            }
        )

        self.assertTrue(chatflow_rule.requires_visible_output)
        self.assertFalse(chatflow_rule.allows_side_effect_only)
        self.assertFalse(workflow_rule.requires_visible_output)
        self.assertTrue(workflow_rule.allows_side_effect_only)
        self.assertEqual(workflow_rule.model_dump(by_alias=True)["allowsSideEffectOnly"], True)

    def test_workflow_api_reexports_runtime_dag_edge_schema(self) -> None:
        self.assertIs(WorkflowEdgeSpec, EdgeSpec)


if __name__ == "__main__":
    unittest.main()
