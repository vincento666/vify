from app.modules.agent_execution import (
    AgentExecutionCapabilities,
    AgentExecutionCapabilityError,
    AgentExecutionStatus,
    SubagentExecutionRef,
)
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.tools import ToolRegistry
from tests.support.ai_assistant_memory_repo import InMemoryAiAssistantRepository


def test_tool_lifecycle_events_share_one_stable_activity_id() -> None:
    repository = InMemoryAiAssistantRepository()
    service = AiAssistantHarnessService(
        repository,
        tool_registry=ToolRegistry.with_demo_tools(),
    )
    session = service.create_session("activity correlation")

    result = service.run_message(
        int(session["id"]),
        "读取上下文",
        tool_name="echo_context",
        tool_input={"message": "读取上下文"},
    )

    tool_events = [
        event
        for event in repository.list_run_events(int(result.run["id"]))
        if str(event["type"]).startswith("tool.call_")
    ]
    activity_ids = {
        str(event["correlation_ids"].get("activityId") or "")
        for event in tool_events
    }

    assert [event["type"] for event in tool_events] == [
        "tool.call_started",
        "tool.call_output",
        "tool.call_completed",
    ]
    assert len(activity_ids) == 1
    assert next(iter(activity_ids)).startswith("tool:")


def test_real_child_execution_result_emits_subagent_lifecycle_event() -> None:
    repository = InMemoryAiAssistantRepository()
    registry = ToolRegistry.with_builtin_tools(
        child_execution_adapter=_RunningSubagentAdapter(),
    )
    service = AiAssistantHarnessService(repository, tool_registry=registry)
    session = service.create_session("subagent activity")

    result = service.run_message(
        int(session["id"]),
        "检查客服子任务",
        tool_name="customer_assistant_subagent_bridge",
        tool_input={"sessionId": 12, "runId": 34},
    )

    subagent_events = [
        event
        for event in repository.list_run_events(int(result.run["id"]))
        if str(event["type"]).startswith("subagent.execution_")
    ]

    assert len(subagent_events) == 1
    assert subagent_events[0]["type"] == "subagent.execution_started"
    assert subagent_events[0]["status"] == "RUNNING"
    assert subagent_events[0]["payload"]["executionId"] == "customer-assistant-run-34"
    assert subagent_events[0]["correlation_ids"]["activityId"] == "subagent:customer-assistant-run-34"


def test_approval_events_share_approval_activity_id() -> None:
    repository = InMemoryAiAssistantRepository()
    service = AiAssistantHarnessService(
        repository,
        tool_registry=ToolRegistry.with_demo_tools(),
    )
    session = service.create_session("approval correlation")

    result = service.run_message(
        int(session["id"]),
        "更新客户资料",
        tool_name="update_customer_profile",
        tool_input={"customerId": "C-1", "field": "name", "value": "New Name"},
    )
    service.deny(int(result.approval_id or 0), "operator", "not approved")

    approval_events = [
        event
        for event in repository.list_run_events(int(result.run["id"]))
        if str(event["type"]).startswith("approval.")
    ]

    assert [event["type"] for event in approval_events] == [
        "approval.required",
        "approval.denied",
    ]
    assert {
        event["correlation_ids"]["activityId"]
        for event in approval_events
    } == {f"approval:{result.approval_id}"}


class _RunningSubagentAdapter:
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
        return SubagentExecutionRef(
            execution_id="customer-assistant-run-34",
            provider=self.provider,
            child_run_id="34",
            agent_type="customer_assistant",
            display_name=self.display_name,
            status=AgentExecutionStatus.RUNNING,
            current_summary="正在检索订单",
            status_ref="/api/v1/customer-assistant/runs/34",
            event_stream_ref="/api/v1/customer-assistant/sessions/12/events/stream",
            result_ref="/api/v1/customer-assistant/runs/34",
            parent_execution_id=parent_execution_id,
            capabilities=self.capabilities,
            scope={"tenantId": "tenant-a"},
            audit={"runId": 34},
            cancellation={"supported": False},
        )

    def observe(self, *, execution_id: str) -> SubagentExecutionRef:
        return self.attach(
            parent_execution_id="",
            session_id=12,
            run_id=34,
        )

    def cancel(self, *, execution_id: str, actor_id: str) -> SubagentExecutionRef:
        raise AgentExecutionCapabilityError("cancel")
