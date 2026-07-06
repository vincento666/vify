import json
import unittest
from collections.abc import Generator
from typing import Any

from fastapi.testclient import TestClient

from app.main import app
from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
from app.modules.ai_assistant.web.router import get_ai_assistant_service
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from tests.support.ai_assistant_memory_repo import InMemoryAiAssistantRepository


class AiAssistantLiveQwenApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._repository = InMemoryAiAssistantRepository()
        self._fake_client = FakeStreamingOpenAIChatClient(
            streamed_chunks=["我会读取项目文件，", "调用技能，并把写文件动作放入审批。"],
            response_payload={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "我会读取项目文件，调用技能，并把写文件动作放入审批。",
                            "tool_calls": [
                                {
                                    "id": "call_read",
                                    "type": "function",
                                    "function": {
                                        "name": "read_workspace_file",
                                        "arguments": '{"path":"README.md"}',
                                    },
                                },
                                {
                                    "id": "call_skill",
                                    "type": "function",
                                    "function": {
                                        "name": "invoke_skill",
                                        "arguments": '{"skillName":"tdd","instruction":"说明红绿重构步骤"}',
                                    },
                                },
                                {
                                    "id": "call_write",
                                    "type": "function",
                                    "function": {
                                        "name": "write_workspace_file",
                                        "arguments": '{"path":"tmp/live-qwen.txt","content":"demo"}',
                                    },
                                },
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )
        app.dependency_overrides[get_ai_assistant_service] = self._service_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_ai_assistant_service, None)

    def test_live_qwen_message_emits_openrouter_stream_chunks_before_model_completion(self) -> None:
        client = TestClient(app)
        try:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "中文 Qwen 会话"})
            session_id = created.json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "请读取 README，调用 tdd skill，然后准备写入摘要",
                    "idempotencyKey": "live-qwen-contract-1",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector")
        finally:
            client.close()

        self.assertEqual(message.status_code, 200, message.text)
        self.assertTrue(message.json()["data"]["approvalRequired"])
        self.assertEqual(self._fake_client.captured_payload["model"], "qwen/qwen3.6-27b")

        event_list = events.json()["data"]["list"]
        titles = [event["visibleTitle"] for event in event_list]
        for title in ["模型调用开始", "思考摘要", "流式输出", "工具调用决策", "文件操作意图", "技能调用意图", "任务编排", "需要审批"]:
            self.assertIn(title, titles)
        stream_events = [event for event in event_list if event["type"] == "model.stream_chunk"]
        self.assertEqual(stream_events[0]["payload"]["streaming"], True)
        self.assertEqual(stream_events[0]["payload"]["source"], "openrouter_delta")
        first_stream_sequence = min(event["sequence"] for event in stream_events)
        model_completed_sequence = next(
            event["sequence"] for event in event_list if event["type"] == "model.call_completed"
        )
        self.assertLess(first_stream_sequence, model_completed_sequence)
        self.assertEqual(inspector.json()["data"]["usage"]["inputTokens"], 10)
        self.assertEqual(inspector.json()["data"]["usage"]["outputTokens"], 5)
        self.assertEqual(inspector.json()["data"]["usage"]["totalTokens"], 15)
        self.assertFalse(inspector.json()["data"]["usage"]["estimated"])

    def test_live_qwen_message_uses_request_model_config_in_openai_payload(self) -> None:
        client = TestClient(app)
        try:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "按请求覆盖 live 模型"})
            session_id = created.json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "请读取 README，调用 tdd skill，然后准备写入摘要",
                    "idempotencyKey": "live-qwen-contract-model-config",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                    "modelConfig": {
                        "provider": "openrouter",
                        "baseUrl": "https://openrouter.example/api/v1",
                        "model": "qwen/qwen3.5-32b",
                        "apiKey": "sk-test-redacted",
                        "apiKeyRef": "env:OPENROUTER_API_KEY_ALT",
                        "temperature": 0.35,
                        "maxTokens": 256,
                    },
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
        finally:
            client.close()

        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual(self._fake_client.captured_payload["model"], "qwen/qwen3.5-32b")
        self.assertEqual(self._fake_client.captured_payload["temperature"], 0.35)
        self.assertEqual(self._fake_client.captured_payload["max_tokens"], 256)
        model_started = next(
            event for event in events.json()["data"]["list"] if event["type"] == "model.call_started"
        )
        self.assertEqual(model_started["payload"]["provider"], "openrouter")
        self.assertEqual(model_started["payload"]["model"], "qwen/qwen3.5-32b")
        self.assertNotIn("sk-test-redacted", json.dumps(events.json(), ensure_ascii=False))
        self.assertNotIn("sk-test-redacted", json.dumps(message.json(), ensure_ascii=False))

    def test_live_qwen_run_interleaves_model_text_tool_echo_and_final_model_output(self) -> None:
        self._fake_client.replace_response(
            streamed_chunks=["我先读取 README，", "再根据工具结果总结。"],
            response_payload={
                "choices": [
                    {
                        "message": {
                            "role": "assistant",
                            "content": "我先读取 README，再根据工具结果总结。",
                            "tool_calls": [
                                {
                                    "id": "call_read",
                                    "type": "function",
                                    "function": {
                                        "name": "read_workspace_file",
                                        "arguments": '{"path":"README.md"}',
                                    },
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {"prompt_tokens": 12, "completion_tokens": 6, "total_tokens": 18},
            },
        )
        client = TestClient(app)
        try:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "ReAct 穿插回显"})
            session_id = created.json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "读取 README 并说明当前项目是什么",
                    "idempotencyKey": "live-qwen-contract-interleave",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
        finally:
            client.close()

        self.assertEqual(message.status_code, 200, message.text)
        self.assertFalse(message.json()["data"]["approvalRequired"])
        final_answer = message.json()["data"]["finalAnswer"]
        self.assertIn("我先读取 README，再根据工具结果总结。", final_answer)

        event_list = events.json()["data"]["list"]
        first_model_stream = next(event for event in event_list if event["type"] == "model.stream_chunk")
        tool_started = next(event for event in event_list if event["type"] == "tool.call_started")
        tool_output = next(event for event in event_list if event["type"] == "tool.call_output")
        tool_completed = next(event for event in event_list if event["type"] == "tool.call_completed")
        final_model_stream = next(
            event
            for event in event_list
            if event["type"] == "model.stream_chunk" and event["payload"].get("phase") == "final_answer"
        )
        run_completed = next(event for event in event_list if event["type"] == "run.completed")

        self.assertLess(first_model_stream["sequence"], tool_started["sequence"])
        self.assertLess(tool_started["sequence"], tool_output["sequence"])
        self.assertLess(tool_output["sequence"], tool_completed["sequence"])
        self.assertLess(tool_completed["sequence"], final_model_stream["sequence"])
        self.assertLess(final_model_stream["sequence"], run_completed["sequence"])
        self.assertIn("我先读取 README", final_model_stream["visibleSummary"])

    def test_live_qwen_react_loop_feeds_tool_result_back_to_model_for_next_tool_decision(self) -> None:
        self._fake_client.replace_script(
            [
                (
                    ["先读取 AGENTS.md，"],
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "先读取 AGENTS.md，再根据结果继续规划。",
                                    "tool_calls": [
                                        {
                                            "id": "call_read_agents",
                                            "type": "function",
                                            "function": {
                                                "name": "read_workspace_file",
                                                "arguments": '{"path":"AGENTS.md"}',
                                            },
                                        }
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
                    },
                ),
                (
                    ["读取完成，继续记录 skill 并准备写入。"],
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "读取完成，继续记录 skill 并准备写入。",
                                    "tool_calls": [
                                        {
                                            "id": "call_skill",
                                            "type": "function",
                                            "function": {
                                                "name": "invoke_skill",
                                                "arguments": '{"skillName":"tdd","instruction":"记录 UAT 红绿重构"}',
                                            },
                                        },
                                        {
                                            "id": "call_write",
                                            "type": "function",
                                            "function": {
                                                "name": "write_workspace_file",
                                                "arguments": '{"path":"tmp/react-loop-summary.md","content":"summary"}',
                                            },
                                        },
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {"prompt_tokens": 40, "completion_tokens": 8, "total_tokens": 48},
                    },
                ),
            ]
        )
        client = TestClient(app)
        try:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "多轮 ReAct"})
            session_id = created.json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "读取 AGENTS.md，再调用 tdd skill，最后准备写入 tmp/react-loop-summary.md",
                    "idempotencyKey": "live-qwen-contract-react-loop",
                    "modelMode": "live",
                    "approvalMode": "smart_approval",
                },
            )
            run_id = message.json()["data"]["runId"]
            events = client.get(f"/api/v1/ai-assistant/runs/{run_id}/events")
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector")
        finally:
            client.close()

        self.assertEqual(message.status_code, 200, message.text)
        self.assertTrue(message.json()["data"]["approvalRequired"])
        self.assertEqual(message.json()["data"]["status"], "WAITING_APPROVAL")
        self.assertEqual(len(self._fake_client.captured_payloads), 2)
        second_messages = self._fake_client.captured_payloads[1]["messages"]
        self.assertEqual(second_messages[-1]["role"], "tool")
        self.assertEqual(second_messages[-1]["tool_call_id"], "call_read_agents")
        self.assertIn("AGENTS.md", second_messages[-1]["content"])

        event_list = events.json()["data"]["list"]
        read_output_sequence = next(
            event["sequence"]
            for event in event_list
            if event["type"] == "tool.call_output" and event["payload"]["toolName"] == "read_workspace_file"
        )
        second_model_stream_sequence = next(
            event["sequence"]
            for event in event_list
            if event["type"] == "model.stream_chunk" and "读取完成" in event["visibleSummary"]
        )
        skill_started_sequence = next(
            event["sequence"]
            for event in event_list
            if event["type"] == "tool.call_started" and event["payload"]["toolName"] == "invoke_skill"
        )
        approval_sequence = next(event["sequence"] for event in event_list if event["type"] == "approval.required")

        self.assertLess(read_output_sequence, second_model_stream_sequence)
        self.assertLess(second_model_stream_sequence, skill_started_sequence)
        self.assertLess(skill_started_sequence, approval_sequence)
        self.assertEqual(
            [tool["toolName"] for tool in inspector.json()["data"]["toolCalls"]],
            ["read_workspace_file", "invoke_skill"],
        )
        self.assertEqual(inspector.json()["data"]["approvalQueue"][0]["toolName"], "write_workspace_file")

    def test_live_qwen_allows_same_file_read_after_write_in_later_react_round(self) -> None:
        self._fake_client.replace_script(
            [
                (
                    ["我先确认记录文件是否存在。"],
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "我先确认记录文件是否存在。",
                                    "tool_calls": [
                                        {
                                            "id": "call_pre_read",
                                            "type": "function",
                                            "function": {
                                                "name": "read_workspace_file",
                                                "arguments": '{"path":"tmp/react-loop-readback-contract.md"}',
                                            },
                                        }
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {"prompt_tokens": 20, "completion_tokens": 5, "total_tokens": 25},
                    },
                ),
                (
                    ["文件不存在，我写入后再核对。"],
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "文件不存在，我写入后再核对。",
                                    "tool_calls": [
                                        {
                                            "id": "call_write_readback",
                                            "type": "function",
                                            "function": {
                                                "name": "write_workspace_file",
                                                "arguments": '{"path":"tmp/react-loop-readback-contract.md","content":"readback ok"}',
                                            },
                                        },
                                        {
                                            "id": "call_post_read",
                                            "type": "function",
                                            "function": {
                                                "name": "read_workspace_file",
                                                "arguments": '{"path":"tmp/react-loop-readback-contract.md"}',
                                            },
                                        },
                                    ],
                                },
                                "finish_reason": "tool_calls",
                            }
                        ],
                        "usage": {"prompt_tokens": 40, "completion_tokens": 8, "total_tokens": 48},
                    },
                ),
                (
                    ["核对完成。"],
                    {
                        "choices": [
                            {
                                "message": {
                                    "role": "assistant",
                                    "content": "核对完成。",
                                    "tool_calls": [],
                                },
                                "finish_reason": "stop",
                            }
                        ],
                        "usage": {"prompt_tokens": 60, "completion_tokens": 4, "total_tokens": 64},
                    },
                ),
            ]
        )
        client = TestClient(app)
        try:
            created = client.post("/api/v1/ai-assistant/sessions", json={"title": "同路径回读"})
            session_id = created.json()["data"]["id"]
            message = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                json={
                    "message": "确认 tmp/react-loop-readback-contract.md，必要时写入，写完后核对一遍内容",
                    "idempotencyKey": "live-qwen-contract-read-after-write",
                    "modelMode": "live",
                    "approvalMode": "always_approve",
                },
            )
            run_id = message.json()["data"]["runId"]
            inspector = client.get(f"/api/v1/ai-assistant/runs/{run_id}/inspector")
        finally:
            client.close()

        self.assertEqual(message.status_code, 200, message.text)
        self.assertEqual(message.json()["data"]["status"], "COMPLETED")
        self.assertEqual(
            [tool["toolName"] for tool in inspector.json()["data"]["toolCalls"]],
            ["read_workspace_file", "write_workspace_file", "read_workspace_file"],
        )
        self.assertEqual(inspector.json()["data"]["toolCalls"][2]["output"]["content"], "readback ok")

    def _service_override(self) -> Generator[AiAssistantHarnessService, None, None]:
        yield AiAssistantHarnessService(
            self._repository,
            live_planner=QwenLivePlanner(
                LivePlannerConfig(
                    base_url="https://openrouter.ai/api/v1",
                    model="qwen/qwen3.6-27b",
                    api_key_ref="env:OPENROUTER_API_KEY",
                    provider="openrouter",
                ),
                client=self._fake_client,
            ),
        )


class FakeStreamingOpenAIChatClient(FakeOpenAIChatClient):
    def __init__(self, *, streamed_chunks: list[str], response_payload: dict[str, Any]) -> None:
        super().__init__(response_payload=response_payload)
        self._streamed_chunks = streamed_chunks
        self._script: list[tuple[list[str], dict[str, Any]]] = []

    def stream_complete(self, payload: dict[str, Any], on_delta=None) -> dict[str, Any]:
        self.captured_payload = payload
        self.captured_payloads.append(payload)
        if self._script:
            streamed_chunks, response_payload = self._script.pop(0)
            if on_delta is not None:
                for chunk in streamed_chunks:
                    on_delta(chunk)
            return response_payload
        if on_delta is not None:
            for chunk in self._streamed_chunks:
                on_delta(chunk)
        if self._response_payload is None:
            raise AssertionError("response payload is required for stream_complete")
        return self._response_payload

    def replace_response(self, *, streamed_chunks: list[str], response_payload: dict[str, Any]) -> None:
        self._streamed_chunks = streamed_chunks
        self._response_payload = response_payload
        self._script = []

    def replace_script(self, script: list[tuple[list[str], dict[str, Any]]]) -> None:
        self._script = list(script)


if __name__ == "__main__":
    unittest.main()
