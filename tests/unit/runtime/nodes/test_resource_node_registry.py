from app.modules.runtime.api.node_registry import NODE_EXECUTOR_REGISTRY


def test_resource_nodes_are_marked_dag_isolated_and_durable() -> None:
    for node_type in {"LLM", "KNOWLEDGE", "AGENT_CALL"}:
        entry = NODE_EXECUTOR_REGISTRY[node_type]
        assert entry.dag_context_isolated is True
        assert entry.node_run_status == "durable"
        assert entry.runtime_event == "node_event"
