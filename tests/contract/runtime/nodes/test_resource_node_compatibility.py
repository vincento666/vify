from app.modules.workflow.domain.runtime_v2 import RuntimeV2CompatibilityChecker


def test_runtime_v2_accepts_resource_node_fanout_compatibility_contract() -> None:
    nodes = [
        {"nodeKey": "start", "type": "START", "config": {"ports": [{"key": "default", "allowFanOut": True}]}},
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
        {"nodeKey": "exec_1", "type": "EXECUTE_WORKFLOW", "config": {"targetWorkflowId": 2}},
        {"nodeKey": "end", "type": "END", "config": {"outputVariable": "final"}},
    ]
    edges = [
        {"sourceNodeKey": "start", "targetNodeKey": "api_1"},
        {"sourceNodeKey": "start", "targetNodeKey": "tool_1"},
        {"sourceNodeKey": "start", "targetNodeKey": "exec_1"},
        {"sourceNodeKey": "api_1", "targetNodeKey": "end"},
        {"sourceNodeKey": "tool_1", "targetNodeKey": "end"},
        {"sourceNodeKey": "exec_1", "targetNodeKey": "end"},
    ]

    result = RuntimeV2CompatibilityChecker.check(nodes, edges)

    assert result["supported"], result
