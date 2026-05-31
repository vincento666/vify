from pydantic import BaseModel, ConfigDict, Field


class AgentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    system_prompt: str = Field(default="", alias="systemPrompt")
    model_config_id: int = Field(alias="modelConfigId")
    temperature: float = 0.7
    max_tokens: int = Field(default=2048, alias="maxTokens")
    max_context_turns: int = Field(default=10, alias="maxContextTurns")
    tool_ids: list[int] = Field(default_factory=list, alias="toolIds")
    knowledge_base_id: int | None = Field(default=None, alias="knowledgeBaseId")
    workflow_id: int | None = Field(default=None, alias="workflowId")


class AgentUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str
    description: str = ""
    system_prompt: str = Field(default="", alias="systemPrompt")
    model_config_id: int = Field(alias="modelConfigId")
    temperature: float = 0.7
    max_tokens: int = Field(default=2048, alias="maxTokens")
    max_context_turns: int = Field(default=10, alias="maxContextTurns")
    knowledge_base_id: int | None = Field(default=None, alias="knowledgeBaseId")
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
