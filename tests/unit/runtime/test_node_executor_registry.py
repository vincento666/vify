from app.modules.runtime.api.node_registry import (
    FIRST_CLASS_NODE_TYPES,
    NODE_EXECUTOR_REGISTRY,
    node_compatibility_matrix,
)
from app.modules.workflow.domain.runtime_v2 import RuntimeV2CompatibilityChecker


EXPECTED_FIRST_CLASS_NODE_TYPES = {
    "START",
    "MESSAGE",
    "QUESTION",
    "HUMAN_INPUT",
    "LLM",
    "CODE",
    "TEXT_PROCESS",
    "JSON_PARSE",
    "VARIABLE_ASSIGN",
    "VARIABLE_AGGREGATION",
    "CONDITION",
    "INTENT_RECOGNITION",
    "INFORMATION_COLLECTION",
    "KNOWLEDGE",
    "API_CALL",
    "TOOL_CALL",
    "EXECUTE_WORKFLOW",
    "TRANSFER_TO_HUMAN",
    "AGENT_CALL",
    "END",
}


def test_runtime_v2_node_registry_covers_all_first_class_nodes() -> None:
    compatibility = RuntimeV2CompatibilityChecker.check(nodes=[], edges=[])

    assert set(FIRST_CLASS_NODE_TYPES) == EXPECTED_FIRST_CLASS_NODE_TYPES
    assert set(compatibility["supportedNodeTypes"]) == EXPECTED_FIRST_CLASS_NODE_TYPES
    assert set(NODE_EXECUTOR_REGISTRY) == EXPECTED_FIRST_CLASS_NODE_TYPES


def test_runtime_v2_node_registry_exposes_executor_and_observability_contracts() -> None:
    matrix = node_compatibility_matrix()

    assert len(matrix) == len(EXPECTED_FIRST_CLASS_NODE_TYPES)
    for node_type, entry in NODE_EXECUTOR_REGISTRY.items():
        assert entry.node_type == node_type
        assert entry.executor
        assert entry.node_run_status in {"durable", "virtual"}
        assert entry.runtime_event in {"node_event", "run_event"}
        assert entry.dag_context_isolated is True
        assert entry.compatibility_status in {"native", "virtual", "reused"}
        assert node_type in matrix
