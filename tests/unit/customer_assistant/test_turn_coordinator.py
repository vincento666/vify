import unittest

from app.modules.customer_assistant.domain.controller import DeterministicTaskRecognitionController
from app.modules.customer_assistant.domain.models import AssistantTurnResult, TaskLedger, TaskCommandType
from app.modules.customer_assistant.domain.policy import CustomerAssistantActionPolicy, UnsupportedTaskCommand
from app.modules.customer_assistant.domain.turn_coordinator import (
    AssistantTurnContext,
    CustomerTurnCoordinator,
)


class CustomerAssistantTurnCoordinatorTest(unittest.TestCase):
    def test_coordinator_runs_one_recognize_validate_act_finalize_cycle(self) -> None:
        controller = DeterministicTaskRecognitionController()
        policy = CustomerAssistantActionPolicy()
        context = AssistantTurnContext(
            session_id=7,
            run_id=11,
            message="我要退票，也想问下行李额",
            ledger=TaskLedger(session_id=7),
        )
        seen: dict[str, object] = {}

        def action_handler(commands):
            seen["commands"] = commands
            return {"applied": [command.task_key for command in commands]}

        def finalizer(observation):
            seen["observation"] = observation
            return AssistantTurnResult(
                run_id=11,
                session_id=7,
                reply_type="DRAFT",
                operator_recommendation="2 tasks",
                customer_reply_draft="draft",
                task_summaries=[{"taskKey": key} for key in observation.action_result["applied"]],
            )

        result = CustomerTurnCoordinator(controller, policy).run(
            context,
            action_handler,
            finalizer,
        )

        command_types = [command.type for command in seen["commands"]]
        command_keys = [command.task_key for command in seen["commands"]]
        self.assertEqual(command_types, [TaskCommandType.ADD_TASK, TaskCommandType.ADD_TASK])
        self.assertEqual(command_keys, ["refund_ticket", "baggage_qa"])
        self.assertEqual(result.operator_recommendation, "2 tasks")
        self.assertEqual(result.task_summaries, [{"taskKey": "refund_ticket"}, {"taskKey": "baggage_qa"}])

    def test_policy_rejects_unsupported_task_command_before_act(self) -> None:
        policy = CustomerAssistantActionPolicy()

        with self.assertRaises(UnsupportedTaskCommand):
            policy.validate([object()])  # type: ignore[list-item]

    def test_natural_refund_phrase_with_flight_number_starts_refund_task(self) -> None:
        controller = DeterministicTaskRecognitionController()

        commands = controller.recognize("退 MU5137 的票", TaskLedger(session_id=8))

        self.assertEqual([command.type for command in commands], [TaskCommandType.ADD_TASK])
        self.assertEqual([command.task_key for command in commands], ["refund_ticket"])


if __name__ == "__main__":
    unittest.main()
