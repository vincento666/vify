from datetime import datetime
import time
import unittest

from app.core.database import Base, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.modules.mcp.api.facade import McpFacade


class McpBoundToolExecutionTest(unittest.TestCase):
    def test_executes_tool_only_when_bound_server_exposes_it(self) -> None:
        server_id = _seed_mcp_server("mock://tools")

        with get_session_factory()() as session:
            result = McpFacade(session).execute_tool_call(
                [server_id],
                "lookup_order",
                {"orderId": "A-100"},
            )

        self.assertTrue(result.success)
        self.assertEqual("Order A-100 status: SHIPPED", result.result)

    def test_rejects_unbound_tool_name(self) -> None:
        server_id = _seed_mcp_server("mock://tools")

        with get_session_factory()() as session:
            result = McpFacade(session).execute_tool_call(
                [server_id],
                "unknown_tool",
                {},
            )

        self.assertFalse(result.success)
        self.assertEqual("Tool is not bound to this agent: unknown_tool", result.error_message)


def _seed_mcp_server(endpoint: str) -> int:
    initialise_database()
    register_baseline_tables()
    mcp_server = Base.metadata.tables["mcp_server"]
    now = datetime.now()
    with get_session_factory()() as session:
        server_id = session.execute(
            mcp_server.insert().values(
                name=f"Bound MCP {time.time_ns()}",
                endpoint=endpoint,
                description="",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            )
        ).inserted_primary_key[0]
        session.commit()
    return int(server_id)


if __name__ == "__main__":
    unittest.main()
