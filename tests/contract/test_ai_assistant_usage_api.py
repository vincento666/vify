import json
import os
import tempfile
import unittest
from collections.abc import Generator
from datetime import datetime
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantUsageApiTest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_usage_api",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace = tempfile.TemporaryDirectory()
        self._other_workspace = tempfile.TemporaryDirectory()
        self._memory = tempfile.TemporaryDirectory()
        self._previous_workspace = os.environ.get("HIFY_WORKSPACE_ROOT")
        self._previous_memory = os.environ.get("HIFY_AI_ASSISTANT_MEMORY_ROOT")
        self._previous_prices = os.environ.get("HIFY_AI_ASSISTANT_MODEL_PRICES_JSON")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace.name
        os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._memory.name
        os.environ["HIFY_AI_ASSISTANT_MODEL_PRICES_JSON"] = json.dumps(
            {
                "version": "test-v1",
                "prices": {
                    "openrouter:qwen/estimated": {
                        "inputUsdPerMillion": "1",
                        "outputUsdPerMillion": "2",
                    }
                },
            }
        )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

        scope = access_scope_for_workspace(
            trusted_user_id="alice",
            trusted_workspace_root=self._workspace.name,
        )
        with self._factory() as session:
            repository = AiAssistantRepository(session, access_scope=scope)
            first_session = repository.create_session(title="First session")
            second_session = repository.create_session(title="Second session")
            first_run = repository.create_run(
                session_id=first_session["id"],
                user_message="actual",
                idempotency_key="usage-api-actual",
            )
            second_run = repository.create_run(
                session_id=first_session["id"],
                user_message="estimated",
                idempotency_key="usage-api-estimated",
            )
            third_run = repository.create_run(
                session_id=second_session["id"],
                user_message="unknown",
                idempotency_key="usage-api-unknown",
            )
            repository.record_model_usage_call(
                session_id=first_session["id"],
                run_id=first_run["id"],
                call_id="planner:1",
                call_kind="planner",
                provider="openrouter",
                model="qwen/actual",
                usage=normalize_model_usage(
                    {"prompt_tokens": 10, "completion_tokens": 5, "cost": "0.01"}
                ),
                started_at=datetime(2026, 7, 10, 15, 30),
                completed_at=datetime(2026, 7, 10, 15, 31),
            )
            repository.record_model_usage_call(
                session_id=first_session["id"],
                run_id=second_run["id"],
                call_id="planner:1",
                call_kind="planner",
                provider="openrouter",
                model="qwen/estimated",
                usage=normalize_model_usage({"prompt_tokens": 20, "completion_tokens": 5}),
                started_at=datetime(2026, 7, 10, 16, 30),
                completed_at=datetime(2026, 7, 10, 16, 31),
            )
            repository.record_model_usage_call(
                session_id=second_session["id"],
                run_id=third_run["id"],
                call_id="planner:1",
                call_kind="planner",
                provider="other",
                model="missing",
                usage=normalize_model_usage({"total_tokens": 20}),
                started_at=datetime(2026, 7, 11, 1, 0),
                completed_at=datetime(2026, 7, 11, 1, 1),
            )
            other_scope = access_scope_for_workspace(
                trusted_user_id="alice",
                trusted_workspace_root=self._other_workspace.name,
            )
            other_repository = AiAssistantRepository(session, access_scope=other_scope)
            other_session = other_repository.create_session(title="Other workspace")
            other_run = other_repository.create_run(
                session_id=other_session["id"],
                user_message="foreign",
                idempotency_key="usage-api-foreign-workspace",
            )
            other_repository.record_model_usage_call(
                session_id=other_session["id"],
                run_id=other_run["id"],
                call_id="planner:1",
                call_kind="planner",
                provider="openrouter",
                model="qwen/foreign",
                usage=normalize_model_usage(
                    {"prompt_tokens": 999, "completion_tokens": 0, "cost": "1"}
                ),
                started_at=datetime(2026, 7, 11, 1, 0),
            )
        self.first_session_id = first_session["id"]
        self.second_session_id = second_session["id"]
        self.other_session_id = other_session["id"]

    def tearDown(self) -> None:
        for key, previous in {
            "HIFY_WORKSPACE_ROOT": self._previous_workspace,
            "HIFY_AI_ASSISTANT_MEMORY_ROOT": self._previous_memory,
            "HIFY_AI_ASSISTANT_MODEL_PRICES_JSON": self._previous_prices,
        }.items():
            if previous is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = previous
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._workspace.cleanup()
        self._other_workspace.cleanup()
        self._memory.cleanup()

    def test_scoped_usage_endpoints_reconcile_tokens_costs_dimensions_and_timezone_days(self) -> None:
        headers = {"X-Hify-Actor-Id": "alice"}
        query = "from=2026-07-10&to=2026-07-11&timezone=Asia%2FShanghai"
        with TestClient(app) as client:
            summary = client.get(f"/api/v1/ai-assistant/usage/summary?{query}", headers=headers)
            daily = client.get(f"/api/v1/ai-assistant/usage/daily?{query}", headers=headers)
            sessions = client.get(f"/api/v1/ai-assistant/usage/sessions?{query}", headers=headers)
            dimensions = client.get(f"/api/v1/ai-assistant/usage/dimensions?{query}", headers=headers)
            detail = client.get(
                f"/api/v1/ai-assistant/usage/sessions/{self.first_session_id}?{query}",
                headers=headers,
            )
            denied = client.get(
                f"/api/v1/ai-assistant/usage/sessions/{self.first_session_id}?{query}",
                headers={"X-Hify-Actor-Id": "bob"},
            )
            foreign_workspace_detail = client.get(
                f"/api/v1/ai-assistant/usage/sessions/{self.other_session_id}?{query}",
                headers=headers,
            )
            bob_summary = client.get(
                f"/api/v1/ai-assistant/usage/summary?{query}",
                headers={"X-Hify-Actor-Id": "bob"},
            )
            bob_daily = client.get(
                f"/api/v1/ai-assistant/usage/daily?{query}",
                headers={"X-Hify-Actor-Id": "bob"},
            )
            bob_sessions = client.get(
                f"/api/v1/ai-assistant/usage/sessions?{query}",
                headers={"X-Hify-Actor-Id": "bob"},
            )
            bob_dimensions = client.get(
                f"/api/v1/ai-assistant/usage/dimensions?{query}",
                headers={"X-Hify-Actor-Id": "bob"},
            )

        self.assertEqual(summary.status_code, 200, summary.text)
        cumulative = summary.json()["data"]["cumulative"]
        self.assertEqual(cumulative["totalTokens"], 60)
        self.assertEqual(cumulative["costUsd"], "0.0100300000")
        self.assertEqual(cumulative["costState"], "partial")
        self.assertEqual(cumulative["unknownCostCount"], 1)
        self.assertEqual(cumulative["unknownCostTokens"], 20)
        self.assertEqual(cumulative["sessionCount"], 2)
        self.assertEqual(
            [(row["date"], row["totalTokens"]) for row in daily.json()["data"]["list"]],
            [("2026-07-10", 15), ("2026-07-11", 45)],
        )
        self.assertEqual([row["totalTokens"] for row in sessions.json()["data"]["list"]], [40, 20])
        self.assertEqual(dimensions.json()["data"]["tokenTypes"]["total"], 60)
        self.assertEqual(detail.json()["data"]["totalTokens"], 40)
        self.assertEqual(len(detail.json()["data"]["calls"]), 2)
        self.assertEqual(denied.status_code, 404)
        self.assertEqual(foreign_workspace_detail.status_code, 404)
        self.assertEqual(bob_summary.json()["data"]["cumulative"]["totalTokens"], 0)
        self.assertEqual(bob_daily.json()["data"]["list"], [])
        self.assertEqual(bob_sessions.json()["data"]["list"], [])
        self.assertEqual(bob_dimensions.json()["data"]["providers"], [])
        self.assertEqual(bob_dimensions.json()["data"]["models"], [])
        self.assertEqual(bob_dimensions.json()["data"]["tokenTypes"]["total"], 0)

    def test_deleted_session_usage_remains_visible_and_drillable(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        with self._factory() as session:
            repository = AiAssistantRepository(
                session,
                access_scope=access_scope_for_workspace(
                    trusted_user_id="alice",
                    trusted_workspace_root=self._workspace.name,
                ),
            )
            self.assertTrue(repository.delete_session(self.second_session_id))

        query = "from=2026-07-10&to=2026-07-11&timezone=Asia%2FShanghai"
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            sessions = client.get(
                f"/api/v1/ai-assistant/usage/sessions?{query}",
                headers=headers,
            ).json()["data"]["list"]
            detail = client.get(
                f"/api/v1/ai-assistant/usage/sessions/{self.second_session_id}?{query}",
                headers=headers,
            )

        deleted = next(row for row in sessions if row["sessionId"] == self.second_session_id)
        self.assertIn("已删除", deleted["title"])
        self.assertEqual(detail.status_code, 200)
        self.assertTrue(detail.json()["data"]["sessionDeleted"])
        self.assertEqual(detail.json()["data"]["totalTokens"], 20)

    def test_daily_session_and_dimension_rankings_use_database_aggregates(self) -> None:
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        query = "from=2026-07-10&to=2026-07-11&timezone=Asia%2FShanghai"
        headers = {"X-Hify-Actor-Id": "alice"}
        with patch.object(
            AiAssistantRepository,
            "list_model_usage_calls",
            side_effect=AssertionError("rankings must not load individual usage rows"),
        ):
            with TestClient(app) as client:
                daily = client.get(
                    f"/api/v1/ai-assistant/usage/daily?{query}",
                    headers=headers,
                )
                sessions = client.get(
                    f"/api/v1/ai-assistant/usage/sessions?{query}",
                    headers=headers,
                )
                dimensions = client.get(
                    f"/api/v1/ai-assistant/usage/dimensions?{query}",
                    headers=headers,
                )

        self.assertEqual(daily.status_code, 200, daily.text)
        self.assertEqual(sessions.status_code, 200, sessions.text)
        self.assertEqual(dimensions.status_code, 200, dimensions.text)

    def test_session_and_call_pagination_preserve_aggregate_totals(self) -> None:
        query = "from=2026-07-10&to=2026-07-11&timezone=Asia%2FShanghai"
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as client:
            sessions = client.get(
                f"/api/v1/ai-assistant/usage/sessions?{query}&limit=1&offset=1",
                headers=headers,
            )
            detail = client.get(
                f"/api/v1/ai-assistant/usage/sessions/{self.first_session_id}"
                f"?{query}&limit=1&offset=1",
                headers=headers,
            )

        self.assertEqual(sessions.status_code, 200, sessions.text)
        self.assertEqual(sessions.json()["data"]["total"], 2)
        self.assertEqual(len(sessions.json()["data"]["list"]), 1)
        self.assertEqual(detail.status_code, 200, detail.text)
        self.assertEqual(detail.json()["data"]["totalTokens"], 40)
        self.assertEqual(detail.json()["data"]["callCount"], 2)
        self.assertEqual(len(detail.json()["data"]["calls"]), 1)

    def test_usage_range_larger_than_one_year_is_rejected(self) -> None:
        with TestClient(app) as client:
            response = client.get(
                "/api/v1/ai-assistant/usage/daily?from=2025-01-01&to=2026-07-11",
                headers={"X-Hify-Actor-Id": "alice"},
            )
        self.assertEqual(response.status_code, 400)

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


if __name__ == "__main__":
    unittest.main()
