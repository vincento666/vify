from __future__ import annotations

from typing import Any

from app.modules.mcp.domain.client import McpToolDetail


class McpToolSchemaBuilder:
    def build(self, tools: list[McpToolDetail]) -> list[dict[str, Any]]:
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.input_schema or {"type": "object", "properties": {}},
            }
            for tool in tools
        ]
