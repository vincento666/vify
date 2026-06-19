from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class RuntimeLabMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    session_id: int | None = Field(default=None, alias="sessionId")
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")
    enabled_sop_ids: list[str] | None = Field(default=None, alias="enabledSopIds")
    route_settings: dict[str, Any] | None = Field(default=None, alias="routeSettings")


class RuntimeLabFallbackAgentRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = True
    agent_id: int | None = Field(default=None, alias="agentId")


class RuntimeLabTemporaryModelTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model: str
    base_url: str = Field(alias="baseUrl")
    api_key: str = Field(default="", alias="apiKey")
    temperature: float | None = 0.0
    max_tokens: int | None = Field(default=8, alias="maxTokens")
    top_p: float | None = Field(default=None, alias="topP")
    provider_type: str = Field(default="OPENAI_COMPATIBLE", alias="providerType")
