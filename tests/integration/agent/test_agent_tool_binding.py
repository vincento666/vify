from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class AgentToolBindingTest(unittest.TestCase):
    def test_replace_tools_deduplicates_and_persists(self) -> None:
        model_id = _seed_model()
        first_tool_id, second_tool_id = _seed_mcp_servers()

        with TestClient(app) as client:
            created = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Tool Agent {time.time_ns()}",
                    "modelConfigId": model_id,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                    "toolIds": [first_tool_id, first_tool_id],
                },
            ).json()["data"]
            self.assertEqual(created["toolIds"], [first_tool_id])

            response = client.put(
                f"/api/v1/agents/{created['id']}/tools",
                json={"toolIds": [second_tool_id, first_tool_id, second_tool_id]},
            )

            self.assertEqual(response.status_code, 200)
            detail = client.get(f"/api/v1/agents/{created['id']}").json()["data"]
            self.assertEqual(detail["toolIds"], [first_tool_id, second_tool_id])

    def test_replace_tools_rejects_missing_tool(self) -> None:
        model_id = _seed_model()

        with TestClient(app) as client:
            created = client.post(
                "/api/v1/agents",
                json={
                    "name": f"Missing Tool Agent {time.time_ns()}",
                    "modelConfigId": model_id,
                    "temperature": 0.7,
                    "maxTokens": 2048,
                    "maxContextTurns": 10,
                    "toolIds": [],
                },
            ).json()["data"]

            response = client.put(
                f"/api/v1/agents/{created['id']}/tools",
                json={"toolIds": [987654321]},
            )

            self.assertEqual(response.status_code, 422)


def _seed_model() -> int:
    initialise_database()
    register_baseline_tables()
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"Tool Binding Provider {time.time_ns()}",
                type="OPENAI",
                base_url="mock://success",
                auth_config={"api_key": "sk-test"},
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="Tool Binding Model",
                model_id="tool-binding-model",
                context_size=4096,
                extra_params={},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(model_id)


def _seed_mcp_servers() -> tuple[int, int]:
    initialise_database()
    register_baseline_tables()
    mcp_server = Base.metadata.tables["mcp_server"]
    now = datetime.now()
    ids: list[int] = []
    with get_session_factory()() as session:
        for suffix in ("A", "B"):
            server_id = session.execute(
                mcp_server.insert().values(
                    name=f"Tool Server {suffix} {time.time_ns()}",
                    endpoint=f"mock://tool-{suffix.lower()}",
                    description="tool binding fixture",
                    enabled=True,
                    deleted=False,
                    created_at=now,
                    updated_at=now,
                )
            ).inserted_primary_key[0]
            ids.append(int(server_id))
        session.commit()
    return ids[0], ids[1]


if __name__ == "__main__":
    unittest.main()
