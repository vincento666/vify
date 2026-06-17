from pydantic import BaseModel, Field


class CreateAiAssistantSessionRequest(BaseModel):
    title: str = ""
    context: dict[str, object] = Field(default_factory=dict)


class SendAiAssistantMessageRequest(BaseModel):
    message: str
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")

    model_config = {"populate_by_name": True}
