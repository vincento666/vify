from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class McpServerCreateRequest(BaseModel):
    name: str
    endpoint: str
    description: str = ""


class McpServerUpdateRequest(BaseModel):
    name: str | None = None
    endpoint: str | None = None
    description: str | None = None
    enabled: int | None = None


class McpServerResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    endpoint: str
    description: str
    enabled: int
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")
    tools: list[str] = Field(default_factory=list)


class McpServerPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[McpServerResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class McpTestResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    latency_ms: int = Field(alias="latencyMs")
    tools: list[str]
    error_message: str | None = Field(alias="errorMessage")


class McpToolDetailResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str
    input_schema: dict[str, object] | None = Field(alias="inputSchema")
    required_params: list[str] | None = Field(alias="requiredParams")


class McpDebugRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool_name: str = Field(alias="toolName")
    arguments: dict[str, object] = Field(default_factory=dict)


class McpDebugResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    result: str | None
    elapsed_ms: int = Field(alias="elapsedMs")
    error_message: str | None = Field(alias="errorMessage")


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
