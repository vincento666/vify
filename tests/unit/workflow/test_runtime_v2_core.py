import unittest

from app.modules.workflow.domain.runtime_v2 import RuntimeV2CompatibilityChecker, RuntimeV2RefBuilder


class RuntimeV2CoreTest(unittest.TestCase):
    def test_ref_builder_supports_workflow_and_chatflow_owner_types(self) -> None:
        workflow_refs = RuntimeV2RefBuilder.build(owner_type="WORKFLOW", owner_id=7, run_id=11)
        chatflow_refs = RuntimeV2RefBuilder.build(owner_type="CHATFLOW", owner_id=8, run_id=12)

        self.assertEqual(workflow_refs["ownerType"], "WORKFLOW")
        self.assertEqual(workflow_refs["ownerId"], 7)
        self.assertEqual(workflow_refs["eventStreamRef"], "/api/v1/runtime-runs/11/events/stream?afterSequence=0")
        self.assertEqual(chatflow_refs["ownerType"], "CHATFLOW")
        self.assertEqual(chatflow_refs["resultRef"], "/api/v1/runtime-runs/12/result")

    def test_compatibility_checker_rejects_whole_graph_without_node_level_mixing(self) -> None:
        result = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "llm_1", "type": "LLM"},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "llm_1"},
                {"sourceNodeKey": "start", "targetNodeKey": "end"},
            ],
        )

        self.assertFalse(result["supported"])
        self.assertEqual(result["fallbackScope"], "whole_graph")
        self.assertIn({"nodeKey": "llm_1", "nodeType": "LLM"}, result["unsupportedNodes"])
        self.assertIn("branching_edges", result["unsupportedPatterns"])


if __name__ == "__main__":
    unittest.main()
