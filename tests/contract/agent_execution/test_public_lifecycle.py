import pytest

from app.modules.agent_execution import (
    AgentExecutionCapabilities,
    AgentExecutionCapabilityError,
    AgentExecutionStatus,
    AgentExecutionTransitionError,
    SubagentExecutionProvider,
    SubagentExecutionRef,
    build_activity_correlation_ids,
    tool_activity_correlation_ids,
    transition_agent_execution_status,
)


def test_public_subagent_execution_contract_carries_real_lifecycle_and_scope() -> None:
    execution = SubagentExecutionRef(
        execution_id="customer-assistant-run-34",
        provider="customer_assistant",
        child_run_id="34",
        parent_execution_id="ai-assistant-run-9",
        agent_type="customer_assistant",
        display_name="客服助手",
        status=AgentExecutionStatus.RUNNING,
        current_summary="正在检索订单",
        started_at="2026-07-18T10:00:00",
        completed_at=None,
        status_ref="/api/v1/customer-assistant/runs/34",
        event_stream_ref="/api/v1/customer-assistant/sessions/12/events/stream",
        result_ref="/api/v1/customer-assistant/runs/34",
        scope={"tenantId": "tenant-a", "orgId": "org-a"},
        audit={"source": "customer_assistant_run", "runId": 34},
        capabilities=AgentExecutionCapabilities(
            spawn=False,
            attach=True,
            observe=True,
            cancel=False,
        ),
        cancellation={"supported": False},
    )

    assert execution.status.is_active is True
    assert execution.execution_id == "customer-assistant-run-34"
    assert execution.capabilities.observe is True
    assert execution.scope["tenantId"] == "tenant-a"
    assert execution.audit["runId"] == 34
    assert isinstance(_ProviderShape(), SubagentExecutionProvider)


def test_lifecycle_status_is_monotonic_unless_provider_explicitly_reopens() -> None:
    assert (
        transition_agent_execution_status(
            AgentExecutionStatus.RUNNING,
            AgentExecutionStatus.COMPLETED,
        )
        is AgentExecutionStatus.COMPLETED
    )
    with pytest.raises(AgentExecutionTransitionError):
        transition_agent_execution_status(
            AgentExecutionStatus.COMPLETED,
            AgentExecutionStatus.RUNNING,
        )
    assert (
        transition_agent_execution_status(
            AgentExecutionStatus.COMPLETED,
            AgentExecutionStatus.RUNNING,
            reopen=True,
        )
        is AgentExecutionStatus.RUNNING
    )


def test_activity_correlation_covers_public_execution_kinds() -> None:
    assert build_activity_correlation_ids(
        run_id=7,
        event_type="orchestration.phase_started",
        payload={"phase": "reason"},
    ) == {
        "activityId": "run:7:phase:reason",
        "activityKind": "phase",
    }
    assert build_activity_correlation_ids(
        run_id=7,
        event_type="plan.step_started",
        payload={"step": {"id": "step-2"}},
    ) == {
        "activityId": "run:7:step:step-2",
        "activityKind": "step",
    }
    assert tool_activity_correlation_ids(
        run_id=7,
        tool_name="invoke_skill",
        step={"id": "step-2"},
    ) == {
        "activityId": "skill:7:step-2",
        "activityKind": "skill",
        "toolName": "invoke_skill",
        "planStepId": "step-2",
        "parentActivityId": "run:7:step:step-2",
    }
    assert build_activity_correlation_ids(
        run_id=7,
        event_type="approval.required",
        payload={"approvalId": 9},
    )["activityId"] == "approval:9"
    assert build_activity_correlation_ids(
        run_id=7,
        event_type="subagent.execution_started",
        payload={"executionId": "customer-assistant-run-34"},
    )["activityId"] == "subagent:customer-assistant-run-34"


class _ProviderShape:
    @property
    def provider(self) -> str:
        return "customer_assistant"

    @property
    def display_name(self) -> str:
        return "客服助手"

    @property
    def capabilities(self) -> AgentExecutionCapabilities:
        return AgentExecutionCapabilities(
            spawn=False,
            attach=True,
            observe=True,
            cancel=False,
        )

    def spawn(
        self,
        *,
        parent_execution_id: str,
        input_payload: dict[str, object],
    ) -> SubagentExecutionRef:
        raise AgentExecutionCapabilityError("spawn")

    def attach(
        self,
        *,
        parent_execution_id: str,
        session_id: int,
        run_id: int,
    ) -> SubagentExecutionRef:
        raise NotImplementedError

    def observe(self, *, execution_id: str) -> SubagentExecutionRef:
        raise NotImplementedError

    def cancel(self, *, execution_id: str, actor_id: str) -> SubagentExecutionRef:
        raise AgentExecutionCapabilityError("cancel")
