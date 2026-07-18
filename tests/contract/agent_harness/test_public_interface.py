from app.modules.agent_harness import (
    AgentHarness,
    HarnessDecision,
    HarnessRunRequest,
    HarnessRunStatus,
    HarnessToolAuthorization,
    HarnessToolCall,
)


class ReadOnlyOrderLookupProfile:
    def plan(self, request, observations, iteration):
        assert request.input == {"message": "check order", "orderNo": "TK-100"}
        if not observations:
            return HarnessDecision.request_tools(
                HarnessToolCall(
                    call_id="lookup-1",
                    name="lookup_order",
                    arguments={"orderNo": "TK-100"},
                )
            )
        return HarnessDecision.finish(
            {
                "answer": f"order status: {observations[-1].output['status']}",
            }
        )

    def authorize_tool(self, request, call):
        return HarnessToolAuthorization.allow()

    def invoke_tool(self, request, call):
        return {"orderNo": call.arguments["orderNo"], "status": "refundable"}


class PartiallyDeniedBatchProfile:
    def __init__(self) -> None:
        self.invoked = False

    def plan(self, request, observations, iteration):
        return HarnessDecision.request_tools(
            HarnessToolCall(call_id="read-1", name="read_order", arguments={}),
            HarnessToolCall(call_id="write-1", name="delete_order", arguments={}),
        )

    def authorize_tool(self, request, call):
        if call.name == "delete_order":
            return HarnessToolAuthorization.deny("destructive tool denied")
        return HarnessToolAuthorization.allow()

    def invoke_tools(self, request, calls):
        self.invoked = True
        raise AssertionError("a partially denied batch must not execute")

    def invoke_tool(self, request, call):
        self.invoked = True
        return {}


def test_agent_harness_runs_tool_observation_then_final_result() -> None:
    result = AgentHarness().execute(
        HarnessRunRequest(
            run_id="run-1",
            input={"message": "check order", "orderNo": "TK-100"},
            max_iterations=3,
        ),
        ReadOnlyOrderLookupProfile(),
    )

    assert result.status is HarnessRunStatus.COMPLETED
    assert result.output == {"answer": "order status: refundable"}
    assert [event.type for event in result.events] == [
        "harness.started",
        "harness.iteration.started",
        "harness.tool.started",
        "harness.tool.completed",
        "harness.observation.recorded",
        "harness.iteration.started",
        "harness.completed",
    ]


def test_agent_harness_authorizes_entire_batch_before_invoking_any_tool() -> None:
    profile = PartiallyDeniedBatchProfile()

    result = AgentHarness().execute(
        HarnessRunRequest(run_id="run-denied-batch", input={}, max_iterations=1),
        profile,
    )

    assert result.status is HarnessRunStatus.FAILED
    assert result.error_code == "TOOL_NOT_ALLOWED"
    assert result.terminal_tool_call is not None
    assert result.terminal_tool_call.call_id == "write-1"
    assert profile.invoked is False
