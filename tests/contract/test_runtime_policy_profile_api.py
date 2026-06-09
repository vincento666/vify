import tempfile
import unittest
from collections.abc import Generator
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, get_session
from app.main import app


class RuntimePolicyProfileApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp_dir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmp_dir.name) / "runtime_policy.db"
        self._engine = create_engine(f"sqlite:///{db_path}", future=True)
        Base.metadata.create_all(bind=self._engine)
        self._factory = sessionmaker(
            bind=self._engine,
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
        )
        app.dependency_overrides[get_session] = self._session_override

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_session, None)
        self._engine.dispose()
        self._tmp_dir.cleanup()

    def test_profile_crud_api_persists_nested_policy_sections(self) -> None:
        payload = _profile_payload(name="041 default routing")

        with TestClient(app) as client:
            created = client.post("/api/v1/runtime-policy/profiles", json=payload)
            self.assertEqual(created.status_code, 200)
            profile = created.json()["data"]
            profile_id = profile["id"]

            listed = client.get("/api/v1/runtime-policy/profiles")
            fetched = client.get(f"/api/v1/runtime-policy/profiles/{profile_id}")
            updated = client.put(
                f"/api/v1/runtime-policy/profiles/{profile_id}",
                json={
                    **payload,
                    "description": "updated for fallback tuning",
                    "thresholds": {
                        **payload["thresholds"],
                        "strongAcceptThreshold": 0.9,
                    },
                },
            )

        self.assertEqual(profile["name"], "041 default routing")
        self.assertEqual(profile["status"], "draft")
        self.assertEqual(profile["version"], 1)
        self.assertEqual(profile["classifier"]["mode"], "fake")
        self.assertNotIn("apiKey", profile["classifier"])
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(listed.json()["data"]["total"], 1)
        self.assertEqual(fetched.status_code, 200)
        self.assertEqual(fetched.json()["data"]["fallbackAgent"]["type"], "fake")
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()["data"]["version"], 2)
        self.assertEqual(updated.json()["data"]["thresholds"]["strongAcceptThreshold"], 0.9)

    def test_invalid_live_classifier_and_fallback_config_is_rejected(self) -> None:
        payload = _profile_payload(name="041 unsafe live routing")
        payload["classifier"] = {
            **payload["classifier"],
            "mode": "llm",
            "baseUrl": "",
            "apiKeyRef": "",
            "model": "",
        }
        payload["fallbackAgent"] = {
            **payload["fallbackAgent"],
            "type": "existing_agent",
            "agentId": None,
        }

        with TestClient(app) as client:
            response = client.post("/api/v1/runtime-policy/profiles", json=payload)

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["code"], 422)

    def _session_override(self) -> Generator[Session]:
        with self._factory() as session:
            yield session


def _profile_payload(name: str) -> dict[str, object]:
    return {
        "name": name,
        "description": "backend managed runtime policy",
        "status": "draft",
        "mode": "balanced",
        "bindings": {
            "tenantId": "tenant-a",
            "botId": "airline-bot",
            "channel": "web",
            "sopGroup": "airline",
        },
        "thresholds": {
            "strongAcceptThreshold": 0.82,
            "classifierMinConfidence": 0.65,
            "faqKeywordMinScore": 0.76,
            "faqKeywordMinMargin": 0.08,
            "faqSemanticMinScore": 0.78,
            "faqSemanticMinMargin": 0.06,
            "ragMinScore": 0.7,
            "ragLexicalAcceptThreshold": 0.45,
        },
        "classifier": {
            "enabled": True,
            "mode": "fake",
            "providerType": "openai-compatible",
            "baseUrl": "mock://classifier",
            "apiKeyRef": "secret/runtime/classifier",
            "model": "fake-runtime-classifier",
            "fallbackModel": "fake-runtime-fallback",
            "promptTemplate": "Classify airline intent: {{message}}",
            "temperature": 0.0,
            "maxTokens": 64,
            "timeoutSeconds": 5,
            "maxAttempts": 1,
            "retrySleepSeconds": 0.0,
            "responseFormat": "json",
        },
        "faq": {
            "knowledgeBaseIds": [10, 11],
            "exactEnabled": True,
            "semanticEnabled": True,
            "topK": 3,
            "rerank": False,
        },
        "rag": {
            "enabled": True,
            "knowledgeBaseIds": [20],
            "retrievalMode": "hybrid",
            "topK": 5,
            "rerank": True,
        },
        "fallbackAgent": {
            "enabled": True,
            "type": "fake",
            "agentId": None,
            "modelConfigId": None,
            "providerType": "mock",
            "baseUrl": "mock://fallback-agent",
            "apiKeyRef": "secret/runtime/agent",
            "model": "fake-runtime-agent",
            "promptTemplate": "Answer with safe fallback: {{message}}",
            "knowledgeBaseIds": [20],
            "maxClarificationAttempts": 2,
            "allowedResponseTypes": ["answer", "clarify", "handoff"],
            "handoffRecommendationPolicy": "explicit_only",
        },
        "handoff": {
            "enabled": True,
            "triggerGroups": ["explicit_request", "safety"],
            "queue": "airline-support",
            "escalationReasonMap": {"USER_REQUEST": "manual_support"},
        },
        "audit": {
            "createdBy": "contract-test",
            "updatedBy": "contract-test",
            "changeReason": "041.1 contract",
        },
    }
