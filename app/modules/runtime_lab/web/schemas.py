from pydantic import BaseModel, ConfigDict, Field


class RuntimeLabMessageRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    message: str
    idempotency_key: str | None = Field(default=None, alias="idempotencyKey")
