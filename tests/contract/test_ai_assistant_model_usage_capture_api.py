import os
import tempfile
import unittest
from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantModelUsageCaptureApiTest(unittest.TestCase):
    def test_live_react_rounds_use_distinct_call_ids(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
        from app.modules.ai_assistant.domain.tools import ToolRegistry
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.web.router import get_ai_assistant_service

        scripted_client = _ScriptedChatClient(
            [
                {
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_echo",
                                        "type": "function",
                                        "function": {
                                            "name": "echo_context",
                                            "arguments": "{}",
                                        },
                                    }
                                ],
                            }
                        }
                    ],
                    "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
                },
                {
                    "choices": [
                        {"message": {"role": "assistant", "content": "round two complete"}}
                    ],
                    "usage": {"prompt_tokens": 3, "completion_tokens": 1, "total_tokens": 4},
                },
            ]
        )

        def service_override():
            with self._factory() as session:
                yield AiAssistantHarnessService(
                    AiAssistantRepository(
                        session,
                        access_scope=access_scope_for_workspace(
                            trusted_user_id="alice",
                            trusted_workspace_root=self._workspace.name,
                        ),
                    ),
                    live_planner=QwenLivePlanner(
                        LivePlannerConfig(
                            base_url="mock://multi-round",
                            model="qwen/multi-round",
                            api_key="test-only",
                        ),
                        client=scripted_client,
                    ),
                    tool_registry=ToolRegistry.with_demo_tools(),
                )

        app.dependency_overrides[get_ai_assistant_service] = service_override
        headers = {"X-Hify-Actor-Id": "alice"}
        try:
            with TestClient(app) as client:
                session_id = client.post(
                    "/api/v1/ai-assistant/sessions",
                    headers=headers,
                    json={"title": "multi-round usage"},
                ).json()["data"]["id"]
                started = client.post(
                    f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                    headers=headers,
                    json={
                        "message": "use echo then finish",
                        "idempotencyKey": "usage-multi-round",
                        "modelMode": "live",
                        "approvalMode": "always_approve",
                    },
                ).json()["data"]
                completed = client.post(
                    f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
                    headers=headers,
                ).json()["data"]
        finally:
            app.dependency_overrides.pop(get_ai_assistant_service, None)

        self.assertEqual(completed["status"], "COMPLETED")
        with self._factory() as session:
            rows = AiAssistantRepository(
                session,
                access_scope=access_scope_for_workspace(
                    trusted_user_id="alice",
                    trusted_workspace_root=self._workspace.name,
                ),
            ).list_model_usage_calls()
        self.assertEqual([row["call_id"] for row in rows], ["planner:1", "planner:2"])
        self.assertEqual([row["total_tokens"] for row in rows], [7, 4])

    def test_failed_provider_invocation_remains_as_unavailable_usage_row(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.domain.harness import AiAssistantHarnessService
        from app.modules.ai_assistant.domain.live_model import LivePlannerConfig, QwenLivePlanner
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.web.router import get_ai_assistant_service

        def service_override():
            with self._factory() as session:
                yield AiAssistantHarnessService(
                    AiAssistantRepository(
                        session,
                        access_scope=access_scope_for_workspace(
                            trusted_user_id="alice",
                            trusted_workspace_root=self._workspace.name,
                        ),
                    ),
                    live_planner=QwenLivePlanner(
                        LivePlannerConfig(
                            base_url="mock://failing-usage",
                            model="qwen/failing-usage",
                            api_key="test-only",
                        ),
                        client=_FailingChatClient(),
                    ),
                )

        app.dependency_overrides[get_ai_assistant_service] = service_override
        headers = {"X-Hify-Actor-Id": "alice"}
        try:
            with TestClient(app) as client:
                session_id = client.post(
                    "/api/v1/ai-assistant/sessions",
                    headers=headers,
                    json={"title": "failed usage"},
                ).json()["data"]["id"]
                started = client.post(
                    f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                    headers=headers,
                    json={
                        "message": "provider fails",
                        "idempotencyKey": "usage-failed-call",
                        "modelMode": "live",
                    },
                ).json()["data"]
                failed = client.post(
                    f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
                    headers=headers,
                ).json()["data"]
        finally:
            app.dependency_overrides.pop(get_ai_assistant_service, None)

        self.assertEqual(failed["status"], "FAILED")
        with self._factory() as session:
            rows = AiAssistantRepository(
                session,
                access_scope=access_scope_for_workspace(
                    trusted_user_id="alice",
                    trusted_workspace_root=self._workspace.name,
                ),
            ).list_model_usage_calls()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["usage_source"], "unavailable")
        self.assertIsNone(rows[0]["input_tokens"])
        self.assertIsNotNone(rows[0]["completed_at"])

    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_model_usage_capture_api",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace = tempfile.TemporaryDirectory()
        self._memory = tempfile.TemporaryDirectory()
        self._previous_workspace = os.environ.get("HIFY_WORKSPACE_ROOT")
        self._previous_memory = os.environ.get("HIFY_AI_ASSISTANT_MEMORY_ROOT")
        self._previous_worker = getattr(app.state, "ai_assistant_autonomous_worker_enabled", None)
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace.name
        os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._memory.name
        app.state.ai_assistant_autonomous_worker_enabled = False
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            ai_assistant_tool_profile="demo",
        )

    def tearDown(self) -> None:
        if self._previous_workspace is None:
            os.environ.pop("HIFY_WORKSPACE_ROOT", None)
        else:
            os.environ["HIFY_WORKSPACE_ROOT"] = self._previous_workspace
        if self._previous_memory is None:
            os.environ.pop("HIFY_AI_ASSISTANT_MEMORY_ROOT", None)
        else:
            os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._previous_memory
        if self._previous_worker is None:
            app.state.__dict__["_state"].pop("ai_assistant_autonomous_worker_enabled", None)
        else:
            app.state.ai_assistant_autonomous_worker_enabled = self._previous_worker
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace.cleanup()
        self._memory.cleanup()

    def test_live_planner_terminal_usage_creates_one_scoped_call_row(self) -> None:
        headers = {"X-Hify-Actor-Id": "alice"}
        model_config = {
            "provider": "openrouter",
            "baseUrl": "mock://usage",
            "model": "qwen/test-usage",
            "apiKey": "test-only",
        }
        with TestClient(app) as client:
            session_id = client.post(
                "/api/v1/ai-assistant/sessions",
                headers=headers,
                json={"title": "usage capture"},
            ).json()["data"]["id"]
            started = client.post(
                f"/api/v1/ai-assistant/sessions/{session_id}/messages",
                headers=headers,
                json={
                    "message": "answer without tools",
                    "idempotencyKey": "usage-live-call",
                    "modelMode": "live",
                    "modelConfig": model_config,
                },
            ).json()["data"]
            completed = client.post(
                f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
                headers=headers,
                json={"modelConfig": model_config},
            ).json()["data"]
            client.post(
                f"/api/v1/ai-assistant/runs/{started['runId']}/worker/process",
                headers=headers,
                json={"modelConfig": model_config},
            )
            inspector_usage = client.get(
                f"/api/v1/ai-assistant/runs/{started['runId']}/inspector",
                headers=headers,
            ).json()["data"]["usage"]
            aggregate_usage = client.get(
                "/api/v1/ai-assistant/usage/summary?timezone=UTC",
                headers=headers,
            ).json()["data"]["cumulative"]

        self.assertEqual(completed["status"], "COMPLETED")
        with self._factory() as session:
            from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
            from app.modules.ai_assistant.infra.repository import AiAssistantRepository

            scope = access_scope_for_workspace(
                trusted_user_id="alice",
                trusted_workspace_root=self._workspace.name,
            )
            rows = AiAssistantRepository(session, access_scope=scope).list_model_usage_calls()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["session_id"], session_id)
        self.assertEqual(rows[0]["run_id"], started["runId"])
        self.assertEqual(rows[0]["call_id"], "planner:1")
        self.assertEqual(rows[0]["call_kind"], "planner")
        self.assertEqual(rows[0]["provider"], "openrouter")
        self.assertEqual(rows[0]["model"], "qwen/test-usage")
        self.assertGreater(rows[0]["total_tokens"], 0)
        self.assertEqual(inspector_usage["totalTokens"], rows[0]["total_tokens"])
        self.assertEqual(aggregate_usage["totalTokens"], rows[0]["total_tokens"])
        self.assertEqual(aggregate_usage["sessionCount"], 1)
        self.assertEqual(aggregate_usage["callCount"], 1)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()


class _FailingChatClient:
    def complete(self, payload: dict) -> dict:
        raise RuntimeError("provider unavailable")


class _ScriptedChatClient:
    def __init__(self, responses: list[dict]) -> None:
        self._responses = responses

    def complete(self, payload: dict) -> dict:
        return self._responses.pop(0)
