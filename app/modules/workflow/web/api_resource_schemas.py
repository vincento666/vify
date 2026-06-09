from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiResourceCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    method: str = "GET"
    endpoint: str
    auth_mode: str = Field(default="none", alias="authMode")
    headers: list[dict[str, Any]] | dict[str, Any] = Field(default_factory=list)
    body_template: str = Field(default="", alias="bodyTemplate")
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    timeout_ms: int = Field(default=30_000, alias="timeoutMs")
    test_payload: dict[str, Any] = Field(default_factory=dict, alias="testPayload")
    enabled: bool = True


class ApiResourceUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    method: str | None = None
    endpoint: str | None = None
    auth_mode: str | None = Field(default=None, alias="authMode")
    headers: list[dict[str, Any]] | dict[str, Any] | None = None
    body_template: str | None = Field(default=None, alias="bodyTemplate")
    input_schema: dict[str, Any] | None = Field(default=None, alias="inputSchema")
    output_schema: dict[str, Any] | None = Field(default=None, alias="outputSchema")
    timeout_ms: int | None = Field(default=None, alias="timeoutMs")
    test_payload: dict[str, Any] | None = Field(default=None, alias="testPayload")
    enabled: bool | None = None


class ApiResourceTestCallRequest(BaseModel):
    input: dict[str, Any] = Field(default_factory=dict)


class ApiToolCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    display_name: str = Field(default="", alias="displayName")
    description: str = ""
    adapter_type: str = Field(default="API_RESOURCE", alias="adapterType")
    api_resource_id: int | None = Field(default=None, alias="apiResourceId")
    input_schema: dict[str, Any] = Field(default_factory=dict, alias="inputSchema")
    output_schema: dict[str, Any] = Field(default_factory=dict, alias="outputSchema")
    model_callable: bool = Field(default=False, alias="modelCallable")
    enabled: bool = True
    timeout_ms: int = Field(default=30_000, alias="timeoutMs")
    retry_count: int = Field(default=0, alias="retryCount")
    error_behavior: str = Field(default="fail", alias="errorBehavior")


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)
