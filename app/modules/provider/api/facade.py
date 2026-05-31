from sqlalchemy.orm import Session

from app.core.errors import BizError, ErrorCode
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.provider.infra.repository import ProviderRepository


class ProviderModelFacade:
    def __init__(self, session: Session) -> None:
        self._repository = ProviderRepository(session)

    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        row = self._repository.get_enabled_model_config(model_config_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Model config not found or disabled")
        return ModelConfigDto(**row)
