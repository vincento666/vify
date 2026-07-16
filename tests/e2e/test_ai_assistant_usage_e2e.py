import json
import os
import tempfile
import unittest
from collections.abc import Generator
from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.main import app
from tests.support.mysql import mysql8_unittest_database


class AiAssistantUsageE2ETest(unittest.TestCase):
    def setUp(self) -> None:
        from app.modules.ai_assistant.infra.schema import ai_assistant_tables, register_ai_assistant_tables

        self._database = mysql8_unittest_database(
            self,
            "ai_assistant_usage_e2e",
            tables=ai_assistant_tables(),
            register=register_ai_assistant_tables,
        )
        self._engine = self._database.engine
        self._factory = self._database.session_factory
        self._workspace = tempfile.TemporaryDirectory()
        self._memory = tempfile.TemporaryDirectory()
        self._previous_workspace = os.environ.get("HIFY_WORKSPACE_ROOT")
        self._previous_memory = os.environ.get("HIFY_AI_ASSISTANT_MEMORY_ROOT")
        self._previous_prices = os.environ.get("HIFY_AI_ASSISTANT_MODEL_PRICES_JSON")
        os.environ["HIFY_WORKSPACE_ROOT"] = self._workspace.name
        os.environ["HIFY_AI_ASSISTANT_MEMORY_ROOT"] = self._memory.name
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

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
        self._memory.cleanup()

    def test_price_version_and_effective_cost_survive_client_reload_and_price_change(self) -> None:
        from app.modules.ai_assistant.domain.access_scope import access_scope_for_workspace
        from app.modules.ai_assistant.domain.model_usage import normalize_model_usage
        from app.modules.ai_assistant.infra.repository import AiAssistantRepository

        os.environ["HIFY_AI_ASSISTANT_MODEL_PRICES_JSON"] = _price_config("v1", "1", "2")
        scope = access_scope_for_workspace(
            trusted_user_id="alice",
            trusted_workspace_root=self._workspace.name,
        )
        with self._factory() as session:
            repository = AiAssistantRepository(session, access_scope=scope)
            assistant_session = repository.create_session(title="stable price")
            run = repository.create_run(
                session_id=assistant_session["id"],
                user_message="stable",
                idempotency_key="stable-price",
            )
            repository.record_model_usage_call(
                session_id=assistant_session["id"],
                run_id=run["id"],
                call_id="planner:1",
                call_kind="planner",
                provider="openrouter",
                model="qwen/stable",
                usage=normalize_model_usage({"prompt_tokens": 1000, "completion_tokens": 500}),
                started_at=datetime(2026, 7, 11, 2, 0),
            )

        os.environ["HIFY_AI_ASSISTANT_MODEL_PRICES_JSON"] = _price_config("v2", "10", "20")
        headers = {"X-Hify-Actor-Id": "alice"}
        with TestClient(app) as first_client:
            first = first_client.get(
                f"/api/v1/ai-assistant/usage/sessions/{assistant_session['id']}"
                "?from=2026-07-11&to=2026-07-11&timezone=UTC",
                headers=headers,
            ).json()["data"]
        with TestClient(app) as reloaded_client:
            second = reloaded_client.get(
                f"/api/v1/ai-assistant/usage/sessions/{assistant_session['id']}"
                "?from=2026-07-11&to=2026-07-11&timezone=UTC",
                headers=headers,
            ).json()["data"]

        self.assertEqual(first["costUsd"], "0.0020000000")
        self.assertEqual(second["costUsd"], "0.0020000000")
        self.assertEqual(second["calls"][0]["pricingVersion"], "v1")

    def _session_override(self) -> Generator[Session, None, None]:
        with self._factory() as session:
            yield session


def _price_config(version: str, input_price: str, output_price: str) -> str:
    return json.dumps(
        {
            "version": version,
            "prices": {
                "openrouter:qwen/stable": {
                    "inputUsdPerMillion": input_price,
                    "outputUsdPerMillion": output_price,
                }
            },
        }
    )


if __name__ == "__main__":
    unittest.main()
