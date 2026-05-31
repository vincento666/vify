from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

ProviderType = Literal[
    "OPENAI",
    "ANTHROPIC",
    "GEMINI",
    "AZURE_OPENAI",
    "OLLAMA",
    "OPENAI_COMPATIBLE",
    "DEEPSEEK",
]

HealthStatus = Literal["UP", "DOWN", "DEGRADED", "UNKNOWN"]


class ProviderCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    type: ProviderType
    base_url: str = Field(alias="baseUrl")
    description: str = ""
    auth_config: dict[str, str] = Field(default_factory=dict, alias="authConfig")


class ProviderUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    base_url: str | None = Field(default=None, alias="baseUrl")
    description: str | None = None
    auth_config: dict[str, str] | None = Field(default=None, alias="authConfig")
    enabled: bool | None = None


class ModelConfigResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    model_id: str = Field(alias="modelId")
    enabled: bool


class ProviderHealthResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    status: HealthStatus
    last_check_at: str | None = Field(alias="lastCheckAt")
    latency_ms: int | None = Field(alias="latencyMs")
    error_message: str | None = Field(alias="errorMessage")


class ProviderResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    type: ProviderType
    base_url: str = Field(alias="baseUrl")
    description: str
    enabled: bool
    auth_configured: bool = Field(alias="authConfigured")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    models: list[ModelConfigResponse]
    health: ProviderHealthResponse | None


class ProviderPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[ProviderResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
