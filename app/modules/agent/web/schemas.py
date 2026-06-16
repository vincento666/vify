from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    system_prompt: str = Field(default="", alias="systemPrompt")
    opening_message: str = Field(default="", alias="openingMessage")
    suggested_questions: list[str] = Field(default_factory=list, alias="suggestedQuestions")
    variables: list[dict[str, Any]] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    model_config_id: int = Field(alias="modelConfigId")
    temperature: float = 0.7
    max_tokens: int = Field(default=2048, alias="maxTokens")
    max_context_turns: int = Field(default=10, alias="maxContextTurns")
    tool_ids: list[int] = Field(default_factory=list, alias="toolIds")
    tool_policies: dict[str, Any] = Field(default_factory=dict, alias="toolPolicies")
    knowledge_base_id: int | None = Field(default=None, alias="knowledgeBaseId")
    knowledge_base_ids: list[int] = Field(default_factory=list, alias="knowledgeBaseIds")
    retrieval_settings: dict[str, Any] = Field(default_factory=dict, alias="retrievalSettings")
    evaluation_gate: dict[str, Any] = Field(default_factory=dict, alias="evaluationGate")
    access: dict[str, Any] = Field(default_factory=dict)
    sharing: dict[str, Any] = Field(default_factory=dict)
    catalog: dict[str, Any] = Field(default_factory=dict)
    analytics: dict[str, Any] = Field(default_factory=dict)
    workflow_id: int | None = Field(default=None, alias="workflowId")


class AgentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    system_prompt: str = Field(default="", alias="systemPrompt")
    opening_message: str = Field(default="", alias="openingMessage")
    suggested_questions: list[str] = Field(default_factory=list, alias="suggestedQuestions")
    variables: list[dict[str, Any]] = Field(default_factory=list)
    memory: dict[str, Any] = Field(default_factory=dict)
    model_config_id: int = Field(alias="modelConfigId")
    temperature: float = 0.7
    max_tokens: int = Field(default=2048, alias="maxTokens")
    max_context_turns: int = Field(default=10, alias="maxContextTurns")
    tool_policies: dict[str, Any] = Field(default_factory=dict, alias="toolPolicies")
    knowledge_base_id: int | None = Field(default=None, alias="knowledgeBaseId")
    knowledge_base_ids: list[int] = Field(default_factory=list, alias="knowledgeBaseIds")
    retrieval_settings: dict[str, Any] = Field(default_factory=dict, alias="retrievalSettings")
    evaluation_gate: dict[str, Any] = Field(default_factory=dict, alias="evaluationGate")
    access: dict[str, Any] = Field(default_factory=dict)
    sharing: dict[str, Any] = Field(default_factory=dict)
    catalog: dict[str, Any] = Field(default_factory=dict)
    analytics: dict[str, Any] = Field(default_factory=dict)
    workflow_id: int | None = Field(default=None, alias="workflowId")


class AgentListPage(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[dict[str, object]]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class AgentToolBindingRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tool_ids: list[int] = Field(default_factory=list, alias="toolIds")


class AgentVersionCreateRequest(BaseModel):
    name: str = ""


class AgentPublishCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    version_id: int = Field(alias="versionId")
    channel_type: str = Field(default="API", alias="channelType")
    config: dict[str, object] = Field(default_factory=dict)


class AgentPromptOptimizationRequest(BaseModel):
    instruction: str = ""
