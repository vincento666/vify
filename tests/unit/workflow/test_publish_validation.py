from app.modules.workflow.domain.service import _publish_validation


def test_publish_validation_rejects_branch_nodes_without_fallback_edges() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "CHATFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {
                    "node_key": "condition_1",
                    "type": "CONDITION",
                    "config": {
                        "conditionBranches": [{"key": "vip", "name": "VIP"}],
                        "defaultBranch": "normal",
                    },
                },
                {
                    "node_key": "intent_1",
                    "type": "INTENT_RECOGNITION",
                    "config": {
                        "intents": [{"key": "refund", "name": "Refund"}],
                        "defaultIntent": "default",
                    },
                },
                {"node_key": "end", "type": "END", "config": {}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "condition_1", "condition_expr": None},
                {"source_node_key": "condition_1", "target_node_key": "intent_1", "condition_expr": "vip"},
                {"source_node_key": "intent_1", "target_node_key": "end", "condition_expr": "refund"},
            ],
        }
    )

    assert validation["valid"] is False
    assert "condition_1 default branch must connect downstream" in validation["errors"]
    assert "intent_1 fallback branch must connect downstream" in validation["errors"]


def test_publish_validation_rejects_regular_nodes_without_downstream_edges() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "CHATFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {"node_key": "message_1", "type": "MESSAGE", "config": {"content": "hello"}},
                {"node_key": "end", "type": "END", "config": {}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "message_1", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "message_1 default outlet must connect downstream" in validation["errors"]


def test_publish_validation_rejects_error_branch_without_error_edge() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "WORKFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {
                    "node_key": "tool_call_1",
                    "type": "TOOL_CALL",
                    "config": {
                        "resourceType": "MCP_TOOL",
                        "resourceId": "mcp:1:lookup_order",
                        "serverIds": [1],
                        "toolName": "lookup_order",
                        "errorBehavior": "branch",
                    },
                },
                {"node_key": "end", "type": "END", "config": {}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "tool_call_1", "condition_expr": None},
                {"source_node_key": "tool_call_1", "target_node_key": "end", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "tool_call_1 error branch must connect downstream" in validation["errors"]


def test_publish_validation_rejects_unknown_variable_references() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "WORKFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {"node_key": "message_1", "type": "MESSAGE", "config": {"content": "{{missing_node.answer}}"}},
                {"node_key": "end", "type": "END", "config": {"outputVariable": "final", "output": "{{message_1.content}}"}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "message_1", "condition_expr": None},
                {"source_node_key": "message_1", "target_node_key": "end", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "message_1 references unknown variable missing_node.answer" in validation["errors"]


def test_publish_validation_rejects_system_variable_writes() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "CHATFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {
                    "node_key": "variable_assign_1",
                    "type": "VARIABLE_ASSIGN",
                    "config": {
                        "targetScope": "sys",
                        "targetVariable": "query",
                        "source": "{{start.sys.query}}",
                    },
                },
                {"node_key": "end", "type": "END", "config": {"outputVariable": "final", "output": "{{sys.query}}"}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "variable_assign_1", "condition_expr": None},
                {"source_node_key": "variable_assign_1", "target_node_key": "end", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "variable_assign_1 cannot write read-only system variable sys.query" in validation["errors"]


def test_publish_validation_rejects_required_config_and_invalid_types() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "WORKFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {
                    "node_key": "code_1",
                    "type": "CODE",
                    "config": {
                        "language": "python",
                        "code": "",
                        "outputParameters": [{"name": "result", "type": "tuple"}],
                    },
                },
                {"node_key": "end", "type": "END", "config": {"outputVariable": "final", "output": "{{code_1.result}}"}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "code_1", "condition_expr": None},
                {"source_node_key": "code_1", "target_node_key": "end", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "code_1 code is required" in validation["errors"]
    assert "code_1 outputParameters.result has unsupported type tuple" in validation["errors"]


def test_publish_validation_rejects_invalid_model_config_id() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "WORKFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {
                    "node_key": "llm_1",
                    "type": "LLM",
                    "config": {
                        "prompt": "hello",
                        "outputVariable": "answer",
                        "modelConfigId": "not-a-number",
                    },
                },
                {"node_key": "end", "type": "END", "config": {"outputVariable": "final", "output": "{{llm_1.answer}}"}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "llm_1", "condition_expr": None},
                {"source_node_key": "llm_1", "target_node_key": "end", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "llm_1 modelConfigId must be numeric" in validation["errors"]


def test_publish_validation_rejects_api_and_tool_nodes_without_resources() -> None:
    validation = _publish_validation(
        {
            "workflow": {"flowType": "WORKFLOW"},
            "nodes": [
                {"node_key": "start", "type": "START", "config": {}},
                {"node_key": "api_call_1", "type": "API_CALL", "config": {}},
                {"node_key": "tool_call_1", "type": "TOOL_CALL", "config": {"resourceType": "MCP_TOOL"}},
                {"node_key": "end", "type": "END", "config": {}},
            ],
            "edges": [
                {"source_node_key": "start", "target_node_key": "api_call_1", "condition_expr": None},
                {"source_node_key": "api_call_1", "target_node_key": "tool_call_1", "condition_expr": None},
                {"source_node_key": "tool_call_1", "target_node_key": "end", "condition_expr": None},
            ],
        }
    )

    assert validation["valid"] is False
    assert "api_call_1 resourceId is required" in validation["errors"]
    assert "tool_call_1 resourceId is required" in validation["errors"]
    assert "tool_call_1 toolName is required" in validation["errors"]
    assert "tool_call_1 serverIds is required" in validation["errors"]
