from pydantic import BaseModel, Field


class CreateAiAssistantSessionRequest(BaseModel):
    title: str = ""
    context: dict[str, object] = Field(default_factory=dict)


class AiAssistantToolCallRequest(BaseModel):
    tool_name: str = Field(alias="toolName")
    tool_input: dict[str, object] = Field(default_factory=dict, alias="toolInput")

    model_config = {"populate_by_name": True}


class AiAssistantModelConfigRequest(BaseModel):
    provider: str = "openrouter"
    base_url: str = Field(default="https://openrouter.ai/api/v1", alias="baseUrl")
    model: str = "qwen/qwen3.6-27b"
    api_key: str = Field(default="", alias="apiKey")
    api_key_ref: str = Field(default="env:OPENROUTER_API_KEY", alias="apiKeyRef")
    temperature: float = 0
    max_tokens: int = Field(default=1024, alias="maxTokens")

    model_config = {"populate_by_name": True}


class SendAiAssistantMessageRequest(BaseModel):
    message: str
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")
    approval_mode: str = Field(default="smart_approval", alias="approvalMode")
    planning_strategy: str = Field(default="auto_lightweight", alias="planningStrategy")
    tool_name: str = Field(default="echo_context", alias="toolName")
    tool_input: dict[str, object] = Field(default_factory=dict, alias="toolInput")
    tool_calls: list[AiAssistantToolCallRequest] = Field(default_factory=list, alias="toolCalls")
    model_mode: str = Field(default="deterministic", alias="modelMode")
    model_config_request: AiAssistantModelConfigRequest | None = Field(default=None, alias="modelConfig")
    ai_assistant_budget: dict[str, object] = Field(default_factory=dict, alias="aiAssistantBudget")
    model_budget_policy: dict[str, object] = Field(default_factory=dict, alias="modelBudgetPolicy")

    model_config = {"populate_by_name": True}


class ProcessAiAssistantRunWorkerRequest(BaseModel):
    model_config_request: AiAssistantModelConfigRequest | None = Field(default=None, alias="modelConfig")

    model_config = {"populate_by_name": True}


class ApprovalDecisionRequest(BaseModel):
    actor_id: str = Field(default="", alias="actorId")
    reason: str = ""

    model_config = {"populate_by_name": True}
