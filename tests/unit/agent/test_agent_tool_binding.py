import unittest
from datetime import datetime
from typing import Any

from app.modules.agent.domain.service import AgentService
from app.modules.agent.web.schemas import AgentCreateRequest


class AgentToolBindingUnitTest(unittest.TestCase):
    def test_create_replaces_tools_with_deduplicated_ids(self) -> None:
        repository = _FakeAgentRepository()
        service = AgentService(repository, _FakeModelFacade())

        service.create(
            AgentCreateRequest(
                name="Tool Agent",
                modelConfigId=10,
                toolIds=[3, 1, 3, 2, 1],
            )
        )

        self.assertEqual(repository.bound_tool_ids, [3, 1, 2])


class _FakeAgentRepository:
    def __init__(self) -> None:
        self.bound_tool_ids: list[int] | None = None

    def create(self, values: dict[str, Any]) -> dict[str, Any]:
        now = datetime.now()
        return {
            **values,
            "id": 7,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
        }

    def replace_tool_bindings(self, agent_id: int, tool_ids: list[int]) -> None:
        self.bound_tool_ids = tool_ids

    def list_tool_ids(self, agent_id: int) -> list[int]:
        return self.bound_tool_ids or []

    def list_available_tool_ids(self, tool_ids: list[int]) -> list[int]:
        return tool_ids


class _FakeModelFacade:
    def get_enabled_model_config(self, model_config_id: int) -> dict[str, object]:
        return {"id": model_config_id}


if __name__ == "__main__":
    unittest.main()
