from app.modules.runtime.domain.dag_selection import build_runtime_dag_selection_graph


def test_runtime_dag_selection_graph_applies_execution_state_overrides() -> None:
    states = {
        state["nodeKey"]: state
        for state in build_runtime_dag_selection_graph(
            nodes=[
                {"nodeKey": "start", "type": "START"},
                {"nodeKey": "work", "type": "HUMAN_INPUT"},
                {"nodeKey": "end", "type": "END"},
            ],
            edges=[
                {"sourceNodeKey": "start", "targetNodeKey": "work"},
                {"sourceNodeKey": "work", "targetNodeKey": "end"},
            ],
            waiting_node_keys={"work"},
            completed_node_keys={"start"},
        )
    }

    assert states["start"]["state"] == "completed"
    assert states["work"]["state"] == "waiting"
    assert states["end"]["state"] == "selected"
