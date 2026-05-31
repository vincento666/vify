from pydantic import BaseModel, ConfigDict, Field


class ChatSessionCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    agent_id: int = Field(alias="agentId")


class ChatSessionResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    agent_id: int = Field(alias="agentId")
    title: str
    status: str
    created_at: str = Field(alias="createdAt")


class ChatSessionPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[ChatSessionResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class ChatMessageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    session_id: int = Field(alias="sessionId")
    role: str
    content: str
    tokens: int
    finish_reason: str = Field(alias="finishReason")
    latency_ms: int = Field(alias="latencyMs")
    created_at: str = Field(alias="createdAt")


class ChatMessagePageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[ChatMessageResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class ChatMessageCreateRequest(BaseModel):
    content: str
    stream: bool = False


class ChatTurnResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    user_message: ChatMessageResponse = Field(alias="userMessage")
    assistant_message: ChatMessageResponse = Field(alias="assistantMessage")
