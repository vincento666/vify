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
