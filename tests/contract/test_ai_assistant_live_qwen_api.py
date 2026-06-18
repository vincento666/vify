import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from app.modules.chat.domain.llm_request import FakeOpenAIChatClient
from tests.support.mysql import mysql8_unittest_database


class AiAssistantLiveQwenApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_live_qwen",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._fake_client = FakeOpenAIChatClient(
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
            }
        )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_llm_mode="live",
            ai_assistant_openrouter_api_key="",
        )

    def tearDown(self) -> None:
        from app.modules.ai_assistant.web.router import get_ai_assistant_service

        app.dependency_overrides.pop(get_ai_assistant_service, None)
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_live_qwen_message_emits_chinese_model_stream_tool_skill_and_task_events(self) -> None:
        from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.web.router import get_ai_assistant_service

        def service_override() -> Generator[AiAssistantHarnessService, None, None]:
            with self._factory() as session:
                yield AiAssistantHarnessService(
                    AiAssistantRepository(session),
                    live_planner=QwenLivePlanner(
                        LivePlannerConfig(
                            base_url="https://openrouter.ai/api/v1",
                            model="qwen/qwen3.5-27b",
                            api_key_ref="env:OPENROUTER_API_KEY",
                        ),
                        client=self._fake_client,
                    ),
                )

        app.dependency_overrides[get_ai_assistant_service] = service_override

        with TestClient(app) as client:
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

        self.assertEqual(message.status_code, 200, message.text)
        self.assertTrue(message.json()["data"]["approvalRequired"])
        self.assertEqual(self._fake_client.captured_payload["model"], "qwen/qwen3.5-27b")

        event_list = events.json()["data"]["list"]
        titles = [event["visibleTitle"] for event in event_list]
        for title in ["模型调用开始", "思考摘要", "流式输出", "工具调用决策", "文件操作意图", "技能调用意图", "任务编排", "需要审批"]:
            self.assertIn(title, titles)
        model_events = [event for event in event_list if event["type"] == "model.call_started"]
        self.assertEqual(model_events[0]["payload"]["model"], "qwen/qwen3.5-27b")
        stream_events = [event for event in event_list if event["type"] == "model.stream_chunk"]
        self.assertEqual(stream_events[0]["payload"]["streaming"], False)
        self.assertEqual(stream_events[0]["payload"]["source"], "post_completion_split")
        skill_events = [event for event in event_list if event["type"] == "model.skill_intent"]
        self.assertEqual(skill_events[0]["payload"]["execution"], "intent_recorded")
        self.assertTrue(any(event["type"] == "approval.required" for event in event_list))
        self.assertEqual(inspector.json()["data"]["usage"]["inputTokens"], 10)
        self.assertEqual(inspector.json()["data"]["usage"]["outputTokens"], 5)
        self.assertEqual(inspector.json()["data"]["usage"]["totalTokens"], 15)
        self.assertFalse(inspector.json()["data"]["usage"]["estimated"])

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
