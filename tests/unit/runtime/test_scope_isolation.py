from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.domain.runtime_v2 import _clone_context_for_frontier_node


def test_frontier_context_clone_isolates_branch_outputs_until_merge() -> None:
    parent = ExecutionContext()
    parent.set_output("start", {"sys.query": "refund"})

    left = _clone_context_for_frontier_node(parent)
    right = _clone_context_for_frontier_node(parent)

    left.set_output("message_a", {"answer": "left"})

    assert right.get_output("message_a") == {}
    assert right.get_output("start") == {"sys.query": "refund"}
