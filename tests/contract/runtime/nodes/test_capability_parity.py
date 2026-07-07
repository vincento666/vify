from pathlib import Path

from app.modules.runtime.api.node_registry import NODE_EXECUTOR_REGISTRY, node_compatibility_matrix


EXPLICIT_PRODUCT_DIFFERENCES = {"TRANSFER_TO_HUMAN"}


def test_chatflow_workflow_capability_schemas_match_except_product_differences() -> None:
    matrix = node_compatibility_matrix()

    assert set(matrix) == set(NODE_EXECUTOR_REGISTRY)
    for node_type, entry in matrix.items():
        chatflow_schema = entry.get("chatflowCapabilitySchema")
        workflow_schema = entry.get("workflowCapabilitySchema")
        chatflow_only = entry.get("chatflowOnlyCapabilities")
        workflow_only = entry.get("workflowOnlyCapabilities")

        assert chatflow_schema, f"{node_type} must publish Chatflow capability schema"
        assert workflow_schema, f"{node_type} must publish Workflow capability schema"
        assert isinstance(chatflow_only, list), f"{node_type} must publish chatflow-only capability diff"
        assert isinstance(workflow_only, list), f"{node_type} must publish workflow-only capability diff"

        if node_type in EXPLICIT_PRODUCT_DIFFERENCES:
            assert entry.get("productDifference"), f"{node_type} needs explicit product difference"
            assert chatflow_schema != workflow_schema, f"{node_type} should document an intentional difference"
            assert chatflow_only or workflow_only, f"{node_type} should expose capability diff"
        else:
            assert chatflow_schema == workflow_schema, f"{node_type} should keep Chatflow/Workflow parity"
            assert chatflow_only == [], f"{node_type} should not have chatflow-only capabilities"
            assert workflow_only == [], f"{node_type} should not have workflow-only capabilities"
            assert not entry.get("productDifference"), f"{node_type} should not claim product difference"


def test_capability_parity_table_documents_every_first_class_node() -> None:
    doc = Path("docs/runtime/node-compatibility-matrix.md").read_text()

    assert "## Chatflow / Workflow Parity" in doc
    for node_type in NODE_EXECUTOR_REGISTRY:
        assert f"| {node_type} |" in doc
    assert "| TRANSFER_TO_HUMAN |" in doc
    assert "Chatflow-only handoff" in doc
