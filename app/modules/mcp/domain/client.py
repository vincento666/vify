from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse


@dataclass(frozen=True)
class McpConnectionResult:
    success: bool
    latency_ms: int
    tools: list[str]
    error_message: str | None = None


@dataclass(frozen=True)
class McpToolDetail:
    name: str
    description: str
    input_schema: dict[str, object] | None
    required_params: list[str] | None


@dataclass(frozen=True)
class McpCallResult:
    success: bool
    result: str | None
    elapsed_ms: int
    error_message: str | None = None


class FakeMcpClient:
    def __init__(self) -> None:
        self._call_attempts: dict[tuple[str, str, str], int] = {}

    def test_connection(self, endpoint: str) -> McpConnectionResult:
        if endpoint.startswith("mock://tools"):
            tools = [tool.name for tool in self.list_tools(endpoint)]
            return McpConnectionResult(success=True, latency_ms=1, tools=tools)
        if endpoint.startswith("mock://empty"):
            return McpConnectionResult(success=True, latency_ms=1, tools=[])
        return McpConnectionResult(
            success=False,
            latency_ms=0,
            tools=[],
            error_message=f"Unsupported MCP endpoint: {endpoint}",
        )

    def list_tools(self, endpoint: str) -> list[McpToolDetail]:
        if not endpoint.startswith("mock://tools"):
            return []
        return [
            McpToolDetail(
                name="lookup_order",
                description="Look up an order by id",
                input_schema={
                    "type": "object",
                    "properties": {
                        "orderId": {
                            "type": "string",
                            "description": "Order id",
                        }
                    },
                    "required": ["orderId"],
                },
                required_params=["orderId"],
            ),
            McpToolDetail(
                name="refund_order",
                description="Create a mock refund request",
                input_schema={
                    "type": "object",
                    "properties": {
                        "orderId": {"type": "string", "description": "Order id"},
                        "reason": {"type": "string", "description": "Refund reason"},
                    },
                    "required": ["orderId"],
                },
                required_params=["orderId"],
            ),
        ]

    def call_tool(self, endpoint: str, tool_name: str, arguments: dict[str, object]) -> McpCallResult:
        if not endpoint.startswith("mock://tools"):
            return McpCallResult(
                success=False,
                result=None,
                elapsed_ms=0,
                error_message=f"Unsupported MCP endpoint: {endpoint}",
            )
        elapsed_ms = _query_int(endpoint, "elapsed", default=1)
        if _query_bool(endpoint, "fail_once"):
            key = (endpoint, tool_name, repr(sorted(arguments.items())))
            attempts = self._call_attempts.get(key, 0)
            self._call_attempts[key] = attempts + 1
            if attempts == 0:
                return McpCallResult(False, None, elapsed_ms, f"Transient tool failure: {tool_name}")
        if tool_name == "lookup_order":
            order_id = arguments.get("orderId")
            if not order_id:
                return McpCallResult(False, None, elapsed_ms, "orderId is required")
            return McpCallResult(True, f"Order {order_id} status: SHIPPED", elapsed_ms)
        if tool_name == "refund_order":
            order_id = arguments.get("orderId")
            if not order_id:
                return McpCallResult(False, None, elapsed_ms, "orderId is required")
            reason = arguments.get("reason") or "not specified"
            return McpCallResult(True, f"Refund request created for {order_id}: {reason}", elapsed_ms)
        return McpCallResult(False, None, elapsed_ms, f"Unknown tool: {tool_name}")


def _query(endpoint: str) -> dict[str, list[str]]:
    return parse_qs(urlparse(endpoint).query)


def _query_bool(endpoint: str, key: str) -> bool:
    values = _query(endpoint).get(key, [])
    return any(value.lower() in {"1", "true", "yes", "on"} for value in values)


def _query_int(endpoint: str, key: str, default: int) -> int:
    values = _query(endpoint).get(key, [])
    if not values:
        return default
    try:
        return int(values[0])
    except ValueError:
        return default
