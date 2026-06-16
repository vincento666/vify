from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.modules.customer_assistant.domain.controller import DeterministicTaskRecognitionController
from app.modules.customer_assistant.domain.models import AssistantTurnResult, TaskCommand, TaskLedger
from app.modules.customer_assistant.domain.policy import CustomerAssistantActionPolicy


@dataclass(frozen=True)
class AssistantTurnContext:
    session_id: int
    run_id: int
    message: str
    ledger: TaskLedger


@dataclass(frozen=True)
class CoreObservation:
    commands: tuple[TaskCommand, ...]
    action_result: dict[str, Any]


class ControlledReActCore:
    def __init__(
        self,
        controller: DeterministicTaskRecognitionController,
        policy: CustomerAssistantActionPolicy,
        max_iterations: int = 1,
    ) -> None:
        self.max_iterations = max_iterations
        self._controller = controller
        self._policy = policy

    def run(
        self,
        context: AssistantTurnContext,
        action_handler: Callable[[list[TaskCommand]], dict[str, Any]],
        finalizer: Callable[[CoreObservation], AssistantTurnResult],
        command_selector: Callable[[list[TaskCommand]], list[TaskCommand]] | None = None,
    ) -> AssistantTurnResult:
        baseline_commands = self._controller.recognize(context.message, context.ledger)
        commands = command_selector(baseline_commands) if command_selector else baseline_commands
        self._policy.validate(commands)
        action_result = action_handler(commands)
        observation = CoreObservation(commands=tuple(commands), action_result=action_result)
        return finalizer(observation)
