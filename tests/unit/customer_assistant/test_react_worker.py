import time
import unittest

from app.modules.customer_assistant.domain.models import TaskItem, TaskStatus
from app.modules.customer_assistant.domain.react_worker import (
    FakeReactWorkerModel,
    ReactModelAction,
    RestrictedReactWorker,
)
from app.modules.customer_assistant.domain.tool_policy import ReactToolPolicy
from app.modules.customer_assistant.domain.worker_registry import (
    ReactWorkerConfig,
    ReactWorkerRegistry,
    react_worker_registry_from_profiles,
)


class CustomerAssistantReactWorkerTest(unittest.TestCase):
    def test_registry_lookup_and_tool_allowlist(self) -> None:
        config = ReactWorkerConfig(
            worker_ref="refund_status_react",
            task_type="refund_status",
            allowed_tools=("lookup_order",),
            max_iterations=3,
            timeout_ms=1000,
        )
        registry = ReactWorkerRegistry([config])
        policy = ReactToolPolicy(allowed_tools=("lookup_order",), high_risk_tools=("submit_refund",))

        self.assertEqual(registry.lookup("refund_status", "refund_status_react"), config)
        self.assertIsNone(registry.lookup("refund_status", "missing"))
        self.assertTrue(policy.is_allowed("lookup_order"))
        self.assertFalse(policy.is_allowed("submit_refund"))
        self.assertTrue(policy.is_high_risk("submit_refund"))

    def test_registry_derives_react_config_from_worker_profile_refs(self) -> None:
        registry = react_worker_registry_from_profiles(
            [
                {
                    "profileId": "configured_refund_react",
                    "taskKey": "refund_ticket",
                    "taskType": "REFUND",
                    "workerType": "react_worker",
                    "workerRef": "configured_refund_react",
                    "modelPolicyRef": "demo-react-model",
                    "promptRef": "demo-react-prompt",
                    "toolRefs": ["lookup_order"],
                    "toolPolicyRef": "strict-read-before-write",
                    "riskPolicyRef": "manual_confirm_high_risk",
                    "outputSchemaRef": "refund_react_result_v2",
                }
            ]
        )

        config = registry.lookup("REFUND", "configured_refund_react")

        self.assertIsNotNone(config)
        assert config is not None
        self.assertEqual(config.allowed_tools, ("lookup_order",))
        self.assertEqual(config.model_policy_ref, "demo-react-model")
        self.assertEqual(config.prompt_ref, "demo-react-prompt")
        self.assertEqual(config.tool_policy_ref, "strict-read-before-write")
        self.assertEqual(config.risk_policy_ref, "manual_confirm_high_risk")
        self.assertEqual(config.output_schema_ref, "refund_react_result_v2")

    def test_read_only_fake_model_completes_with_summarized_events(self) -> None:
        worker = RestrictedReactWorker(
            config=_config(),
            model=FakeReactWorkerModel(
                [
                    ReactModelAction.request_tool("lookup_order", {"orderNo": "TK-100"}),
                    ReactModelAction.final(
                        operator_recommendation="Order TK-100 is refundable.",
                        customer_reply_draft="订单 TK-100 可按规则退票。",
                    ),
                ]
            ),
            tools={"lookup_order": lambda args: {"orderNo": args["orderNo"], "status": "refundable", "api_key": "secret"}},
        )

        result = worker.run(_task(), "查 TK-100 退票状态")

        event_types = [event["type"] for event in result.events]
        self.assertEqual(result.status, TaskStatus.COMPLETED)
        self.assertEqual(result.customer_reply_draft, "订单 TK-100 可按规则退票。")
        self.assertIn("react_worker_started", event_types)
        self.assertIn("react_tool_call_completed", event_types)
        self.assertIn("react_structured_output_completed", event_types)
        self.assertIn("react_worker_completed", event_types)
        self.assertNotIn("chainOfThought", str(result.events))
        self.assertTrue(all(event["payload"]["schemaVersion"] == "customer_assistant.react_worker.event/1" for event in result.events))
        observation = next(event for event in result.events if event["type"] == "react_observation_recorded")
        self.assertEqual(observation["payload"]["observation"]["schemaVersion"], "customer_assistant.react_observation/1")
        self.assertEqual(observation["payload"]["observation"]["summary"]["api_key"], "[REDACTED]")
        self.assertEqual(result.evidence["structuredOutput"]["schemaVersion"], "customer_assistant.react_final/1")

    def test_disallowed_tool_fails_without_executing_it(self) -> None:
        executed = False

        def forbidden(_args):
            nonlocal executed
            executed = True
            return {}

        worker = RestrictedReactWorker(
            config=_config(),
            model=FakeReactWorkerModel([ReactModelAction.request_tool("delete_order", {"orderNo": "TK-100"})]),
            tools={"delete_order": forbidden},
        )

        result = worker.run(_task(), "删除订单")

        self.assertEqual(result.status, TaskStatus.FAILED)
        self.assertFalse(executed)
        self.assertEqual(result.error["code"], "TOOL_NOT_ALLOWED")

    def test_high_risk_write_becomes_proposed_action(self) -> None:
        worker = RestrictedReactWorker(
            config=_config(allowed_tools=("lookup_order", "submit_refund")),
            model=FakeReactWorkerModel(
                [ReactModelAction.request_tool("submit_refund", {"orderNo": "TK-100"}, risk="write")]
            ),
            tools={"submit_refund": lambda _args: {"shouldNotExecute": True}},
        )

        result = worker.run(_task(), "提交退票")

        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertEqual(result.proposed_actions[0]["actionType"], "submit_refund")
        self.assertEqual(result.proposed_actions[0]["payload"]["orderNo"], "TK-100")
        self.assertEqual(result.proposed_actions[0]["sideEffect"], "proposed-write")
        self.assertTrue(result.proposed_actions[0]["idempotencyKey"].startswith("react:refund_status:"))

    def test_tool_policy_ref_can_require_manual_confirmation_for_read_tool(self) -> None:
        executed = False

        def lookup_order(_args):
            nonlocal executed
            executed = True
            return {"status": "refundable"}

        worker = RestrictedReactWorker(
            config=_config(tool_policy_ref="manual_confirm_lookup_tools"),
            model=FakeReactWorkerModel([ReactModelAction.request_tool("lookup_order", {"orderNo": "TK-100"})]),
            tools={"lookup_order": lookup_order},
        )

        result = worker.run(_task(), "查订单")

        event_types = [event["type"] for event in result.events]
        self.assertEqual(result.status, TaskStatus.WAITING)
        self.assertFalse(executed)
        self.assertEqual(result.proposed_actions[0]["actionType"], "lookup_order")
        self.assertNotIn("react_tool_call_completed", event_types)

    def test_max_iterations_and_timeout_are_enforced(self) -> None:
        looping = RestrictedReactWorker(
            config=_config(max_iterations=1),
            model=FakeReactWorkerModel([ReactModelAction.request_tool("lookup_order", {"orderNo": "TK-100"})]),
            tools={"lookup_order": lambda _args: {"status": "refundable"}},
        )
        slow = RestrictedReactWorker(
            config=_config(timeout_ms=1),
            model=FakeReactWorkerModel([ReactModelAction.request_tool("lookup_order", {"orderNo": "TK-100"})]),
            tools={"lookup_order": lambda _args: _slow_result()},
        )

        self.assertEqual(looping.run(_task(), "查订单").error["code"], "MAX_ITERATIONS_EXCEEDED")
        self.assertEqual(slow.run(_task(), "查订单").error["code"], "WORKER_TIMEOUT")


def _config(
    allowed_tools: tuple[str, ...] = ("lookup_order",),
    max_iterations: int = 3,
    timeout_ms: int = 1000,
    tool_policy_ref: str = "customer_assistant_react_default",
) -> ReactWorkerConfig:
    return ReactWorkerConfig(
        worker_ref="refund_status_react",
        task_type="refund_status",
        allowed_tools=allowed_tools,
        max_iterations=max_iterations,
        timeout_ms=timeout_ms,
        tool_policy_ref=tool_policy_ref,
    )


def _task() -> TaskItem:
    return TaskItem(
        id=77,
        session_id=12,
        task_key="refund_status:TK-100",
        task_type="refund_status",
        business_key="TK-100",
        short_id="REF77",
        status=TaskStatus.PENDING,
        worker_type="react_worker",
        worker_ref="refund_status_react",
    )


def _slow_result() -> dict[str, str]:
    time.sleep(0.01)
    return {"status": "slow"}


if __name__ == "__main__":
    unittest.main()
