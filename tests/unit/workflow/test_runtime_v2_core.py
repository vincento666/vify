import unittest
import time

from app.modules.workflow.domain.runtime_v2 import (
    RuntimeV2CompatibilityChecker,
    RuntimeV2RefBuilder,
    _runtime_v2_handled_error_output,
)


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
                {"nodeKey": "custom_1", "type": "CUSTOM_PLUGIN"},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "custom_1"},
                {"sourceNodeKey": "start", "targetNodeKey": "end"},
            ],
        )

        self.assertFalse(result["supported"])
        self.assertEqual(result["fallbackScope"], "whole_graph")
        self.assertIn({"nodeKey": "custom_1", "nodeType": "CUSTOM_PLUGIN"}, result["unsupportedNodes"])
        self.assertIn("branching_edges", result["unsupportedPatterns"])

    def test_compatibility_checker_accepts_runtime_v2_resource_nodes_and_rejects_unsafe_api_call(self) -> None:
        supported = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "knowledge_1", "type": "KNOWLEDGE"},
                {"nodeKey": "llm_1", "type": "LLM"},
                {"nodeKey": "api_1", "type": "API_CALL", "config": {"resourceId": "api-resource:1"}},
                {
                    "nodeKey": "tool_1",
                    "type": "TOOL_CALL",
                    "config": {
                        "resourceType": "MCP_TOOL",
                        "resourceId": "mcp:1:lookup_order",
                        "serverIds": [1],
                        "toolName": "lookup_order",
                    },
                },
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "knowledge_1"},
                {"sourceNodeKey": "knowledge_1", "targetNodeKey": "llm_1"},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "api_1"},
                {"sourceNodeKey": "api_1", "targetNodeKey": "tool_1"},
                {"sourceNodeKey": "tool_1", "targetNodeKey": "end"},
            ],
        )
        rejected = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "api_1", "type": "API_CALL", "config": {"method": "GET", "url": "https://example.test/raw"}},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "api_1"},
                {"sourceNodeKey": "api_1", "targetNodeKey": "end"},
            ],
        )

        self.assertTrue(supported["supported"], supported)
        self.assertIn("KNOWLEDGE", supported["supportedNodeTypes"])
        self.assertIn("LLM", supported["supportedNodeTypes"])
        self.assertIn("API_CALL", supported["supportedNodeTypes"])
        self.assertIn("TOOL_CALL", supported["supportedNodeTypes"])
        self.assertFalse(rejected["supported"])
        self.assertIn(
            {"nodeKey": "api_1", "nodeType": "API_CALL", "reason": "api_call_requires_api_resource"},
            rejected["unsupportedNodes"],
        )

    def test_compatibility_checker_rejects_branch_nodes_without_fallback_edges(self) -> None:
        condition_result = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {
                    "nodeKey": "condition_1",
                    "type": "CONDITION",
                    "config": {
                        "conditionBranches": [{"key": "vip", "name": "VIP"}],
                        "defaultBranch": "normal",
                    },
                },
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "condition_1"},
                {"sourceNodeKey": "condition_1", "targetNodeKey": "end", "condition": "vip"},
            ],
        )
        intent_result = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {
                    "nodeKey": "intent_1",
                    "type": "INTENT_RECOGNITION",
                    "config": {
                        "intents": [{"key": "refund", "name": "Refund"}],
                        "defaultIntent": "default",
                    },
                },
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "intent_1"},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "end", "condition": "refund"},
            ],
        )

        self.assertFalse(condition_result["supported"])
        self.assertIn("branch_edges_incomplete", condition_result["unsupportedPatterns"])
        self.assertIn("condition_1.default", condition_result["branchValidationErrors"])
        self.assertFalse(intent_result["supported"])
        self.assertIn("branch_edges_incomplete", intent_result["unsupportedPatterns"])
        self.assertIn("intent_1.default", intent_result["branchValidationErrors"])

    def test_compatibility_checker_rejects_regular_nodes_without_downstream_edges(self) -> None:
        result = RuntimeV2CompatibilityChecker.check(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "message_1", "type": "MESSAGE", "config": {"content": "hello"}},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "message_1"},
            ],
        )

        self.assertFalse(result["supported"])
        self.assertIn("node_endpoints_incomplete", result["unsupportedPatterns"])
        self.assertIn("message_1.default", result["branchValidationErrors"])

    def test_error_policy_output_is_standardized_for_all_failure_node_types(self) -> None:
        failure_node_types = ["LLM", "API_CALL", "TOOL_CALL", "CODE", "EXECUTE_WORKFLOW", "AGENT_CALL"]

        for node_type in failure_node_types:
            with self.subTest(node_type=node_type):
                continued = _runtime_v2_handled_error_output(
                    node_type,
                    {"config": {"errorBehavior": "continue", "outputVariable": "answer"}},
                    RuntimeError("boom"),
                    time.perf_counter(),
                )
                branched = _runtime_v2_handled_error_output(
                    node_type,
                    {"config": {"errorBehavior": "branch"}},
                    RuntimeError("boom"),
                    time.perf_counter(),
                )

                self.assertIsNotNone(continued)
                assert continued is not None
                self.assertEqual(continued["success"], False)
                self.assertEqual(continued["error"], "boom")
                self.assertEqual(continued["errorBehavior"], "continue")
                self.assertEqual(continued["answer"], "")
                self.assertNotIn("route", continued)
                self.assertEqual(continued["evidence"]["status"], "FAILED")
                self.assertEqual(continued["evidence"]["handled"], True)

                self.assertIsNotNone(branched)
                assert branched is not None
                self.assertEqual(branched["route"], "error")
                self.assertEqual(branched["evidence"]["route"], "error")

        self.assertIsNone(
            _runtime_v2_handled_error_output(
                "MESSAGE",
                {"config": {"errorBehavior": "continue"}},
                RuntimeError("boom"),
                time.perf_counter(),
            )
        )


if __name__ == "__main__":
    unittest.main()
