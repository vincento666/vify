from typing import Any

from pydantic import BaseModel


class ModelConfigDto(BaseModel):
    id: int
    provider_id: int
    provider_type: str
    provider_base_url: str
    provider_auth_config: dict[str, Any]
    name: str
    model_id: str
    context_size: int
    extra_params: dict[str, Any]
