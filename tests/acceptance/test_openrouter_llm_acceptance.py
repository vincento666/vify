from __future__ import annotations

import json
import os
from pathlib import Path
import unittest
from typing import Any

import httpx

from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser


RUN_LIVE = os.getenv("HIFY_RUN_LIVE_OPENROUTER") == "1"


@unittest.skipUnless(RUN_LIVE, "Set HIFY_RUN_LIVE_OPENROUTER=1 to run live OpenRouter acceptance")
class OpenRouterLlmAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.model = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash")
        self.parser = OpenAIAdapterParser()
        self.artifact_path = Path(
            "artifacts/slices/010-real-tool-calling-and-mcp/010.6/openrouter-llm-acceptance.md"
        )

    def test_chat_tool_call_and_second_round(self) -> None:
        chat_result = self._chat(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a strict acceptance test assistant.",
                    },
                    {
                        "role": "user",
                        "content": "Return only this token: HIFY_LLM_OK",
                    },
                ],
                "temperature": 0,
            }
        )
        parsed_chat = self.parser.parse_chat_response(chat_result)
        self.assertIn("HIFY_LLM_OK", parsed_chat.content)

        first_round = self._chat(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Call lookup_order for orderId A-100. Do not answer directly.",
                    }
                ],
                "tools": [_lookup_order_tool()],
                "tool_choice": {"type": "function", "function": {"name": "lookup_order"}},
                "temperature": 0,
            }
        )
        parsed_first_round = self.parser.parse_chat_response(first_round)
        self.assertEqual(parsed_first_round.finish_reason, "tool_calls")
        self.assertEqual(len(parsed_first_round.tool_calls), 1)
        tool_call = parsed_first_round.tool_calls[0]
        self.assertEqual(tool_call.name, "lookup_order")
        self.assertEqual(tool_call.arguments.get("orderId"), "A-100")

        raw_tool_calls = first_round["choices"][0]["message"]["tool_calls"]
        tool_content = json.dumps(
            {"orderId": "A-100", "status": "paid", "eta": "2026-06-02"},
            ensure_ascii=False,
        )
        second_round = self._chat(
            {
                "model": self.model,
                "messages": [
                    {
                        "role": "user",
                        "content": "Call lookup_order for orderId A-100. Do not answer directly.",
                    },
                    {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": raw_tool_calls,
                    },
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.id,
                        "name": "lookup_order",
                        "content": tool_content,
                    },
                ],
                "temperature": 0,
            }
        )
        parsed_second_round = self.parser.parse_chat_response(second_round)
        self.assertTrue(parsed_second_round.content.strip())

        self._write_artifact(
            chat_content=parsed_chat.content,
            tool_name=tool_call.name,
            tool_arguments=tool_call.arguments,
            final_content=parsed_second_round.content,
        )

    def _chat(self, payload: dict[str, Any]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "X-Title": "Hify OpenRouter acceptance",
        }
        with httpx.Client(timeout=60) as client:
            response = client.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
            )
        if response.status_code >= 400:
            raise AssertionError(
                f"OpenRouter chat completion failed: {response.status_code} {response.text}"
            )
        payload = response.json()
        if not isinstance(payload, dict):
            raise AssertionError("OpenRouter response is not a JSON object")
        return payload

    def _write_artifact(
        self,
        chat_content: str,
        tool_name: str,
        tool_arguments: dict[str, Any],
        final_content: str,
    ) -> None:
        self.artifact_path.parent.mkdir(parents=True, exist_ok=True)
        self.artifact_path.write_text(
            "\n".join(
                [
                    "# OpenRouter LLM Acceptance",
                    "",
                    "- Slice: 010.6 live provider acceptance",
                    f"- Base URL: `{self.base_url}`",
                    f"- Model: `{self.model}`",
                    "- API key: runtime environment only, not recorded",
                    "- Basic chat: passed",
                    "- Tool-call request: passed",
                    "- Tool-call parser: passed",
                    "- Second LLM round: passed",
                    "",
                    "## Evidence",
                    "",
                    f"- Chat token observed: `{chat_content.strip()}`",
                    f"- Tool call: `{tool_name}`",
                    f"- Tool arguments: `{json.dumps(tool_arguments, ensure_ascii=False)}`",
                    f"- Final answer excerpt: `{final_content.strip()[:300]}`",
                    "",
                ]
            ),
            encoding="utf-8",
        )


def _lookup_order_tool() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "lookup_order",
            "description": "Lookup a customer order by order id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "orderId": {
                        "type": "string",
                        "description": "Order id such as A-100.",
                    }
                },
                "required": ["orderId"],
                "additionalProperties": False,
            },
        },
    }
