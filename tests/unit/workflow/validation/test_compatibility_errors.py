from __future__ import annotations

from app.modules.workflow.domain.runtime_v2 import RuntimeV2CompatibilityChecker


def test_runtime_v2_reports_missing_downstream_port_as_readable_error() -> None:
    result = RuntimeV2CompatibilityChecker.check(
        nodes=[
            {"nodeKey": "start", "type": "START"},
            {"nodeKey": "message_1", "type": "MESSAGE", "config": {"content": "hello"}},
            {"nodeKey": "end", "type": "END"},
        ],
        edges=[{"sourceNodeKey": "start", "targetNodeKey": "message_1"}],
    )

    assert not result["supported"]
    assert _error(result, "message_1.default")["message"] == "message_1 default outlet must connect downstream"


def test_runtime_v2_reports_missing_resource_schema_as_readable_error() -> None:
    result = RuntimeV2CompatibilityChecker.check(
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

    assert not result["supported"]
    error = _error(result, "api_1.resourceId")
    assert error["reason"] == "api_call_requires_api_resource"
    assert "API Resource" in error["message"]
    assert "raw URL mode" in error["message"]


def test_runtime_v2_reports_unsupported_field_combination_as_readable_error() -> None:
    result = RuntimeV2CompatibilityChecker.check(
        nodes=[
            {"nodeKey": "start", "type": "START"},
            {
                "nodeKey": "tool_1",
                "type": "TOOL_CALL",
                "config": {
                    "resourceType": "MCP_TOOL",
                    "resourceId": "mcp:1:create_order",
                    "serverIds": [1],
                    "toolName": "create_order",
                },
            },
            {"nodeKey": "end", "type": "END"},
        ],
        edges=[
            {"sourceNodeKey": "start", "targetNodeKey": "tool_1"},
            {"sourceNodeKey": "tool_1", "targetNodeKey": "end"},
        ],
    )

    assert not result["supported"]
    error = _error(result, "tool_1.allowWrite")
    assert error["nodeType"] == "TOOL_CALL"
    assert "allowWrite" in error["message"]


def test_runtime_v2_reports_unknown_variable_reference_as_readable_error() -> None:
    result = RuntimeV2CompatibilityChecker.check(
        nodes=[
            {"nodeKey": "start", "type": "START"},
            {"nodeKey": "message_1", "type": "MESSAGE", "config": {"content": "{{ghost.answer}}"}},
            {"nodeKey": "end", "type": "END"},
        ],
        edges=[
            {"sourceNodeKey": "start", "targetNodeKey": "message_1"},
            {"sourceNodeKey": "message_1", "targetNodeKey": "end"},
        ],
    )

    assert not result["supported"]
    error = _error(result, "message_1.ghost.answer")
    assert error["category"] == "variable_references_invalid"
    assert error["message"] == "message_1 references unknown variable ghost.answer"


def test_runtime_v2_reports_incompatible_node_version_or_target_as_readable_error() -> None:
    result = RuntimeV2CompatibilityChecker.check(
        nodes=[
            {"nodeKey": "start", "type": "START"},
            {"nodeKey": "exec_1", "type": "EXECUTE_WORKFLOW", "config": {"targetWorkflowId": "draft-only"}},
            {"nodeKey": "end", "type": "END"},
        ],
        edges=[
            {"sourceNodeKey": "start", "targetNodeKey": "exec_1"},
            {"sourceNodeKey": "exec_1", "targetNodeKey": "end"},
        ],
    )

    assert not result["supported"]
    error = _error(result, "exec_1.targetWorkflowId")
    assert error["category"] == "node_contract_invalid"
    assert error["message"] == "exec_1 targetWorkflowId must be numeric"


def _error(result: dict[str, object], code: str) -> dict[str, str]:
    errors = result.get("errors")
    assert isinstance(errors, list)
    match = next((error for error in errors if isinstance(error, dict) and error.get("code") == code), None)
    assert match is not None, errors
    return match
