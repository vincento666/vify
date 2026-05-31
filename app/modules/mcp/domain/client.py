from __future__ import annotations

from dataclasses import dataclass


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
        if tool_name == "lookup_order":
            order_id = arguments.get("orderId")
            if not order_id:
                return McpCallResult(False, None, 1, "orderId is required")
            return McpCallResult(True, f"Order {order_id} status: SHIPPED", 1)
        if tool_name == "refund_order":
            order_id = arguments.get("orderId")
            if not order_id:
                return McpCallResult(False, None, 1, "orderId is required")
            reason = arguments.get("reason") or "not specified"
            return McpCallResult(True, f"Refund request created for {order_id}: {reason}", 1)
        return McpCallResult(False, None, 1, f"Unknown tool: {tool_name}")
