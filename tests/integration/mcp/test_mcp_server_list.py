from datetime import datetime
import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app


class McpServerListTest(unittest.TestCase):
    def test_list_mcp_servers_filters_enabled_servers(self) -> None:
        enabled_id, disabled_id = _seed_mcp_servers()

        with TestClient(app) as client:
            response = client.get("/api/v1/mcp-servers", params={"page": 1, "pageSize": 20, "enabled": 1})

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        ids = [item["id"] for item in data["list"]]
        self.assertIn(enabled_id, ids)
        self.assertNotIn(disabled_id, ids)
        self.assertGreaterEqual(data["total"], 1)
        self.assertEqual(data["page"], 1)
        self.assertEqual(data["pageSize"], 20)


def _seed_mcp_servers() -> tuple[int, int]:
    initialise_database()
    register_baseline_tables()
    mcp_server = Base.metadata.tables["mcp_server"]
    now = datetime.now()
    with get_session_factory()() as session:
        enabled_id = session.execute(
            mcp_server.insert().values(
                name=f"Enabled MCP {time.time_ns()}",
                endpoint="mock://enabled-mcp",
                description="enabled fixture",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        disabled_id = session.execute(
            mcp_server.insert().values(
                name=f"Disabled MCP {time.time_ns()}",
                endpoint="mock://disabled-mcp",
                description="disabled fixture",
                enabled=False,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(enabled_id), int(disabled_id)


if __name__ == "__main__":
    unittest.main()
