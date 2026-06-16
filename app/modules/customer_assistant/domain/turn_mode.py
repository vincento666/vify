from enum import StrEnum

from app.modules.customer_assistant.domain.actor import CustomerAssistantActor


class CustomerAssistantTurnMode(StrEnum):
    CUSTOMER_TASK_TURN = "customer_task_turn"
    OPERATOR_RECOMMENDATION_TURN = "operator_recommendation_turn"
    SYSTEM_TRIGGER_TURN = "system_trigger_turn"
    OPERATOR_APPLY_TASK_COMMAND = "operator_apply_task_command"


def classify_customer_assistant_turn(actor: CustomerAssistantActor, _message: str) -> CustomerAssistantTurnMode:
    if actor == "operator":
        return CustomerAssistantTurnMode.OPERATOR_RECOMMENDATION_TURN
    if actor == "system":
        return CustomerAssistantTurnMode.SYSTEM_TRIGGER_TURN
    return CustomerAssistantTurnMode.CUSTOMER_TASK_TURN
