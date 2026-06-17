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

    def test_compatibility_checker_rejects_unknown_nodes_and_unsupported_patterns(self) -> None:
        result = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "tool_1", "type": "TOOL_CALL"},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "tool_1"},
                {"sourceNodeKey": "start", "targetNodeKey": "end"},
            ],
        )

        self.assertFalse(result["supported"])
        self.assertEqual(result["fallbackScope"], "whole_graph")
        self.assertIn({"nodeKey": "tool_1", "nodeType": "TOOL_CALL"}, result["unsupportedNodes"])
        self.assertIn("branching_edges", result["unsupportedPatterns"])

    def test_compatibility_checker_accepts_knowledge_and_llm_but_still_rejects_tool_call(self) -> None:
        supported = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "knowledge_1", "type": "KNOWLEDGE"},
                {"nodeKey": "llm_1", "type": "LLM"},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "knowledge_1"},
                {"sourceNodeKey": "knowledge_1", "targetNodeKey": "llm_1"},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "end"},
            ],
        )
        rejected = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "tool_1", "type": "TOOL_CALL"},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "tool_1"},
                {"sourceNodeKey": "tool_1", "targetNodeKey": "end"},
            ],
        )

        self.assertTrue(supported["supported"], supported)
        self.assertIn("KNOWLEDGE", supported["supportedNodeTypes"])
        self.assertIn("LLM", supported["supportedNodeTypes"])
        self.assertFalse(rejected["supported"])
        self.assertIn({"nodeKey": "tool_1", "nodeType": "TOOL_CALL"}, rejected["unsupportedNodes"])


if __name__ == "__main__":
    unittest.main()
