from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WorkflowNodeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    node_key: str = Field(alias="nodeKey")
    type: str
    name: str = ""
    config: dict[str, object] = Field(default_factory=dict)


class WorkflowEdgeRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_node_key: str = Field(alias="sourceNodeKey")
    target_node_key: str = Field(alias="targetNodeKey")
    condition: str | None = None


class WorkflowCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    nodes: list[WorkflowNodeRequest]
    edges: list[WorkflowEdgeRequest] = Field(default_factory=list)


class WorkflowUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str | None = None
    description: str | None = None
    status: str | None = None
    nodes: list[WorkflowNodeRequest] | None = None
    edges: list[WorkflowEdgeRequest] | None = None


class WorkflowRunRequest(BaseModel):
    input: dict[str, object] = Field(default_factory=dict)


class WorkflowRunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    run_id: int = Field(alias="runId")
    status: str
    output: dict[str, object]


class WorkflowResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    description: str
    flow_type: str = Field(alias="flowType")
    status: str
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class WorkflowPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[WorkflowResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class WorkflowNodeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    node_key: str = Field(alias="nodeKey")
    type: str
    name: str
    config: dict[str, object]


class WorkflowEdgeResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_node_key: str = Field(alias="sourceNodeKey")
    target_node_key: str = Field(alias="targetNodeKey")
    condition: str | None


class WorkflowDetailResponse(WorkflowResponse):
    nodes: list[WorkflowNodeResponse]
    edges: list[WorkflowEdgeResponse]


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
