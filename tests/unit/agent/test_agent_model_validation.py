import unittest

from app.core.errors import BizError, ErrorCode
from app.modules.agent.domain.service import AgentService
from app.modules.agent.web.schemas import AgentCreateRequest


class RejectingModelFacade:
    def get_enabled_model_config(self, _model_config_id: int) -> None:
        raise BizError(ErrorCode.NOT_FOUND, "Model config not found or disabled")


class RecordingRepository:
    def __init__(self) -> None:
        self.created = False

    def create(self, _values: dict[str, object]) -> dict[str, object]:
        self.created = True
        return {}


class AgentModelValidationUnitTest(unittest.TestCase):
    def test_create_rejects_before_repository_write(self) -> None:
        repository = RecordingRepository()
        service = AgentService(repository, RejectingModelFacade())  # type: ignore[arg-type]

        with self.assertRaises(BizError):
            service.create(
                AgentCreateRequest(
                    name="Invalid",
                    modelConfigId=1,
                    temperature=0.7,
                    maxTokens=2048,
                    maxContextTurns=10,
                )
            )

        self.assertFalse(repository.created)


if __name__ == "__main__":
    unittest.main()
