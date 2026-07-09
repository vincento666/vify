from pathlib import Path

from app.modules.runtime.api.node_registry import FIRST_CLASS_NODE_TYPES
from app.modules.runtime.domain.node_evidence_matrix import (
    parse_node_evidence_matrix,
    validate_node_evidence_matrix,
)


DOC_PATH = Path("docs/runtime/node-compatibility-matrix.md")


def test_evidence_matrix_documents_every_first_class_node() -> None:
    rows = parse_node_evidence_matrix(DOC_PATH.read_text())
    errors = validate_node_evidence_matrix(rows, expected_node_types=FIRST_CLASS_NODE_TYPES)

    assert set(rows) == set(FIRST_CLASS_NODE_TYPES)
    assert errors == []


def test_evidence_matrix_validation_fails_when_a_flow_status_is_missing() -> None:
    rows = parse_node_evidence_matrix(
        """
| Node type | Workflow evidence | Chatflow evidence | Closure owner |
|---|---|---|---|
| START | partial |  | spec 223.3 |
"""
    )

    errors = validate_node_evidence_matrix(rows, expected_node_types=("START",))

    assert "START chatflow evidence status is missing" in errors
