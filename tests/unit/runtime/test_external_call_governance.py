from __future__ import annotations

import pytest

from app.modules.runtime.domain.external_call_governance import (
    ExternalCallGovernance,
    ExternalCallGovernanceError,
    ExternalCallPolicy,
)


@pytest.mark.parametrize("call_type", ["LLM", "API", "TOOL", "KNOWLEDGE"])
def test_external_call_governance_retries_and_emits_error_event_for_all_client_types(call_type: str) -> None:
    governance = ExternalCallGovernance()
    attempts: list[int] = []

    def always_times_out() -> object:
        attempts.append(len(attempts) + 1)
        raise TimeoutError(f"{call_type} too slow")

    with pytest.raises(ExternalCallGovernanceError) as raised:
        governance.run(
            call_type=call_type,
            provider_key=f"{call_type.lower()}:primary",
            node_key=f"{call_type.lower()}_1",
            node_run_id=123,
            policy=ExternalCallPolicy(timeout_ms=25, retry_count=2, breaker_failure_threshold=3),
            operation=always_times_out,
        )

    assert attempts == [1, 2, 3]
    assert raised.value.event_type == "workflow_node_external_call_failed"
    assert raised.value.event_payload == {
        "callType": call_type,
        "providerKey": f"{call_type.lower()}:primary",
        "nodeKey": f"{call_type.lower()}_1",
        "nodeRunId": 123,
        "errorKind": "timeout",
        "message": f"{call_type} too slow",
        "attempts": 3,
        "timeoutMs": 25,
        "retryCount": 2,
        "breakerOpen": True,
    }


def test_external_call_governance_open_breaker_skips_operation_until_reset() -> None:
    governance = ExternalCallGovernance()
    calls: list[str] = []
    policy = ExternalCallPolicy(
        timeout_ms=100,
        retry_count=0,
        breaker_failure_threshold=1,
        breaker_reset_ms=60_000,
    )

    def fail_once() -> object:
        calls.append("called")
        raise RuntimeError("provider down")

    with pytest.raises(ExternalCallGovernanceError):
        governance.run(
            call_type="LLM",
            provider_key="openrouter:qwen",
            node_key="llm_1",
            node_run_id=321,
            policy=policy,
            operation=fail_once,
        )

    with pytest.raises(ExternalCallGovernanceError) as raised:
        governance.run(
            call_type="LLM",
            provider_key="openrouter:qwen",
            node_key="llm_1",
            node_run_id=322,
            policy=policy,
            operation=fail_once,
        )

    assert calls == ["called"]
    assert raised.value.event_payload["errorKind"] == "circuit_open"
    assert raised.value.event_payload["attempts"] == 0
    assert raised.value.event_payload["breakerOpen"] is True
