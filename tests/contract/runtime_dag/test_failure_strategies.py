from __future__ import annotations

import time

from app.modules.workflow.domain.graph_validation import validate_node_contracts
from app.modules.workflow.domain.runtime_v2 import _runtime_v2_handled_error_output


def test_failure_strategy_matrix_for_runtime_v2_error_policy_nodes() -> None:
    fail_fast = _runtime_v2_handled_error_output(
        "CODE",
        {"config": {"errorBehavior": "fail"}},
        RuntimeError("boom"),
        time.perf_counter(),
    )
    continued = _runtime_v2_handled_error_output(
        "CODE",
        {"config": {"errorBehavior": "continue", "outputVariable": "answer"}},
        RuntimeError("boom"),
        time.perf_counter(),
    )
    branched = _runtime_v2_handled_error_output(
        "CODE",
        {"config": {"errorBehavior": "branch"}},
        RuntimeError("boom"),
        time.perf_counter(),
    )
    partial = _runtime_v2_handled_error_output(
        "CODE",
        {"config": {"errorBehavior": "partial", "outputVariable": "answer"}},
        RuntimeError("boom"),
        time.perf_counter(),
    )

    assert fail_fast is None
    assert continued is not None
    assert continued["success"] is False
    assert continued["errorBehavior"] == "continue"
    assert continued["answer"] == ""
    assert "route" not in continued

    assert branched is not None
    assert branched["success"] is False
    assert branched["errorBehavior"] == "branch"
    assert branched["route"] == "error"
    assert branched["evidence"]["route"] == "error"

    assert partial is not None
    assert partial["success"] is False
    assert partial["partialSuccess"] is True
    assert partial["errorBehavior"] == "partial"
    assert partial["answer"] == ""
    assert "route" not in partial
    assert partial["evidence"]["failureStrategy"] == "partial_success"
    assert partial["evidence"]["partialSuccess"] is True


def test_partial_failure_strategy_is_valid_dag_node_contract() -> None:
    issues = validate_node_contracts(
        [
            {
                "nodeKey": "code_1",
                "type": "CODE",
                "config": {
                    "code": "result = 1 / 0",
                    "errorBehavior": "partial",
                    "outputVariable": "answer",
                },
            }
        ]
    )

    assert issues == []
