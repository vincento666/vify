from typing import Any
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.modules.customer_assistant.domain.actor import DEFAULT_CUSTOMER_ASSISTANT_ACTOR, CustomerAssistantActor


class CustomerAssistantSessionCreateRequest(BaseModel):
    context: dict[str, Any] = Field(default_factory=dict)


class CustomerAssistantTurnRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")
    actor: CustomerAssistantActor = DEFAULT_CUSTOMER_ASSISTANT_ACTOR


class CustomerAssistantTaskControlRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    control_type: Literal["retry", "cancel", "resume"] = Field(alias="controlType")
    reason: str = ""
    actor: CustomerAssistantActor = "operator"


class CustomerAssistantProposedActionUpdateRequest(BaseModel):
    title: str | None = None
    payload: dict[str, Any] | None = None
    actor: CustomerAssistantActor = "operator"


class CustomerAssistantWorkerProfileUpsertRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    task_key: str = Field(alias="taskKey", min_length=1)
    task_type: str = Field(alias="taskType", min_length=1)
    worker_type: str = Field(alias="workerType", min_length=1)
    worker_ref: str = Field(alias="workerRef", min_length=1)
    model_policy_ref: str = Field(default="default", alias="modelPolicyRef")
    prompt_ref: str = Field(default="default", alias="promptRef")
    tool_refs: list[str] = Field(default_factory=list, alias="toolRefs")
    risk_policy_ref: str = Field(default="manual_confirm", alias="riskPolicyRef")
    enabled: bool = True


class CustomerAssistantSubAgentInput(BaseModel):
    message: str
    actor: CustomerAssistantActor = DEFAULT_CUSTOMER_ASSISTANT_ACTOR


class CustomerAssistantSpawnSubAgentArguments(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_type: Literal["customer_assistant"] = Field(alias="agentType")
    session_id: int | None = Field(default=None, alias="sessionId")
    input: CustomerAssistantSubAgentInput
    event_level: Literal["L1"] = Field(default="L1", alias="eventLevel")


class CustomerAssistantSpawnSubAgentRequest(BaseModel):
    tool: Literal["spawn_sub_agent"]
    arguments: CustomerAssistantSpawnSubAgentArguments
