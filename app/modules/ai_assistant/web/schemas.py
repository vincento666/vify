from pydantic import BaseModel, Field


class CreateAiAssistantSessionRequest(BaseModel):
    title: str = ""
    context: dict[str, object] = Field(default_factory=dict)


class AiAssistantToolCallRequest(BaseModel):
    tool_name: str = Field(alias="toolName")
    tool_input: dict[str, object] = Field(default_factory=dict, alias="toolInput")

    model_config = {"populate_by_name": True}


class SendAiAssistantMessageRequest(BaseModel):
    message: str
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")
    approval_mode: str = Field(default="smart_approval", alias="approvalMode")
    tool_name: str = Field(default="echo_context", alias="toolName")
    tool_input: dict[str, object] = Field(default_factory=dict, alias="toolInput")
    tool_calls: list[AiAssistantToolCallRequest] = Field(default_factory=list, alias="toolCalls")
    model_mode: str = Field(default="deterministic", alias="modelMode")

    model_config = {"populate_by_name": True}


class ApprovalDecisionRequest(BaseModel):
    actor_id: str = Field(alias="actorId")
    reason: str = ""

    model_config = {"populate_by_name": True}
