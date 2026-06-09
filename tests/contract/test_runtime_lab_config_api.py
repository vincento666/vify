import unittest
import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path
import time

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.core.database import Base, get_session
from tests.contract.test_runtime_policy_profile_api import _profile_payload
from app.main import app


class RuntimeLabConfigApiContractTest(unittest.TestCase):
    def test_config_exposes_bindings_arbitrator_model_and_never_api_key(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/runtime-lab/config")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertIn("sopBindings", data)
        self.assertIn("arbitrator", data)
        self.assertIn("mode", data["arbitrator"])
        self.assertIn("model", data["arbitrator"])
        self.assertIn("fallbackModel", data["arbitrator"])
        for binding in data["sopBindings"]:
            self.assertIn("canvasPath", binding)
            self.assertEqual(binding["canvasPath"], f"/chatflows/{binding['chatflowId']}/canvas")
        self.assertNotIn("apiKey", data["arbitrator"])
        self.assertNotIn("api_key", str(data).lower())


class RuntimeLabFallbackAgentConfigApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_lab_fallback_agent_config.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        app.dependency_overrides[get_session] = self._session_override
        app.dependency_overrides[get_settings] = lambda: Settings(_env_file=None)

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        app.dependency_overrides.pop(get_settings, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_config_exposes_current_fallback_agent_and_agent_options(self) -> None:
        with self._factory() as session:
            agent_id = _seed_agent(session, name="航空 FAQ 兜底智能体")
        payload = _profile_payload("034 runtime-lab fallback")
        payload["status"] = "active"
        payload["bindings"] = {**payload["bindings"], "tenantId": "", "botId": "", "channel": "", "sopGroup": ""}
        payload["fallbackAgent"] = {
            **payload["fallbackAgent"],
            "type": "existing_agent",
            "agentId": agent_id,
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=payload)
            self.assertEqual(created.status_code, 200)
            response = client.get("/api/v1/runtime-lab/config")

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["fallbackAgent"]["type"], "existing_agent")
        self.assertEqual(data["fallbackAgent"]["agentId"], agent_id)
        self.assertEqual(data["fallbackAgent"]["agentName"], "航空 FAQ 兜底智能体")
        self.assertTrue(data["fallbackAgent"]["available"])
        self.assertIn(
            {"id": agent_id, "name": "航空 FAQ 兜底智能体", "description": "", "enabled": True},
            data["fallbackAgentOptions"],
        )

    def test_runtime_lab_can_select_existing_agent_as_fallback_without_hardcoding(self) -> None:
        with self._factory() as session:
            agent_id = _seed_agent(session, name="可切换兜底智能体")

        with TestClient(app) as client:
            selected = client.put(
                "/api/v1/runtime-lab/fallback-agent",
                json={"enabled": True, "agentId": agent_id},
            )
            config = client.get("/api/v1/runtime-lab/config")

        self.assertEqual(selected.status_code, 200)
        self.assertEqual(selected.json()["data"]["fallbackAgent"]["type"], "existing_agent")
        self.assertEqual(selected.json()["data"]["fallbackAgent"]["agentId"], agent_id)
        self.assertEqual(config.json()["data"]["fallbackAgent"]["agentName"], "可切换兜底智能体")

    def test_select_fallback_agent_when_env_llm_key_is_missing_does_not_500(self) -> None:
        app.dependency_overrides[get_settings] = lambda: Settings(
            _env_file=None,
            runtime_lab_intent_arbitrator_mode="llm",
            runtime_lab_intent_arbitrator_base_url="https://openrouter.ai/api/v1",
            runtime_lab_intent_arbitrator_model="qwen/qwen3.5-9b",
            runtime_lab_intent_arbitrator_api_key="",
        )
        with self._factory() as session:
            agent_id = _seed_agent(session, name="缺密钥环境兜底智能体")

        with TestClient(app) as client:
            selected = client.put(
                "/api/v1/runtime-lab/fallback-agent",
                json={"enabled": True, "agentId": agent_id},
            )

        self.assertEqual(selected.status_code, 200)
        data = selected.json()["data"]
        self.assertEqual(data["fallbackAgent"]["agentId"], agent_id)
        self.assertEqual(data["arbitrator"]["mode"], "llm")
        self.assertFalse(data["arbitrator"]["apiKeyConfigured"])
        self.assertFalse(data["arbitrator"]["available"])

    def test_selected_existing_agent_answers_unresolved_runtime_lab_turn(self) -> None:
        with self._factory() as session:
            agent_id = _seed_agent(session, name="真实兜底智能体")
        payload = _profile_payload("034 runtime-lab fallback route")
        payload["status"] = "active"
        payload["bindings"] = {**payload["bindings"], "tenantId": "", "botId": "", "channel": "", "sopGroup": ""}
        payload["fallbackAgent"] = {
            **payload["fallbackAgent"],
            "type": "existing_agent",
            "agentId": agent_id,
        }

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=payload)
            self.assertEqual(created.status_code, 200)
            runtime_session = client.post("/api/v1/runtime-lab/sessions").json()["data"]
            response = client.post(
                f"/api/v1/runtime-lab/sessions/{runtime_session['id']}/messages",
                json={
                    "message": "机场大巴末班车几点，航班延误后还能赶上吗？",
                    "idempotencyKey": f"fallback-route-{time.time_ns()}",
                    "enabledSopIds": [],
                },
            )

        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["routeDecision"]["action"], "AGENT_FALLBACK")
        self.assertEqual(data["routeDecision"]["agentAnswer"]["sourceLayer"], "agent_policy")
        self.assertIn("LLM mock:", data["reply"])
        self.assertIn("机场大巴", data["reply"])
        self.assertEqual(data["routeDecision"]["agentAnswer"]["citations"][0]["agentId"], agent_id)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _seed_agent(session: Session, *, name: str) -> int:
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    provider_id = session.execute(
        provider.insert().values(
            name=f"RuntimeLab Fallback Provider {time.time_ns()}",
            type="OPENAI",
            base_url="mock://success",
            auth_config={"api_key": "sk-test"},
            description="",
            enabled=True,
            deleted=False,
            created_at=now,
            updated_at=now,
        )
    ).inserted_primary_key[0]
    model_id = session.execute(
        model_config.insert().values(
            provider_id=provider_id,
            name="RuntimeLab Fallback Model",
            model_id="runtime-lab-fallback-model",
            context_size=4096,
            extra_params={},
            enabled=True,
            deleted=False,
            created_at=now,
            updated_at=now,
        )
    ).inserted_primary_key[0]
    agent_id = session.execute(
        agent.insert().values(
            name=name,
            description="",
            system_prompt="你是民航客服兜底智能体，只回答 FAQ/RAG/SOP 未覆盖的问题。",
            model_config_id=model_id,
            temperature=0.2,
            max_tokens=512,
            max_context_turns=4,
            enabled=True,
            deleted=False,
            created_at=now,
            updated_at=now,
        )
    ).inserted_primary_key[0]
    session.commit()
    return int(agent_id)
