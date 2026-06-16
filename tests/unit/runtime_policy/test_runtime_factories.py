import json
import tempfile
from collections.abc import Generator
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.runtime_lab.domain.agent_fallback import FakeFallbackAgent
from app.modules.runtime_lab.domain.agent_fallback import FallbackAgentRequest
from app.modules.runtime_lab.domain.classifier import ClassifierInput, LlmConstrainedIntentClassifier
from app.modules.runtime_policy.domain.factories import (
    build_agent_output_policy_from_snapshot,
    build_classifier_from_snapshot,
    build_fallback_agent_from_snapshot,
)
from tests.contract.test_runtime_policy_profile_api import _profile_payload


class RuntimePolicyRuntimeFactoryTest(unittest.TestCase):
    def test_classifier_factory_uses_profile_prompt_model_and_runtime_params(self) -> None:
        snapshot = _snapshot()
        snapshot["classifier"] = {
            **snapshot["classifier"],
            "enabled": True,
            "mode": "llm",
            "baseUrl": "https://llm.example.test/v1",
            "apiKeyRef": "secret/runtime/classifier",
            "model": "profile-classifier-model",
            "fallbackModel": "profile-fallback-model",
            "promptTemplate": "PROFILE PROMPT {{message}}",
            "temperature": 0.35,
            "maxTokens": 123,
            "timeoutSeconds": 7,
            "maxAttempts": 2,
            "retrySleepSeconds": 0.1,
        }

        with patch("app.modules.runtime_policy.domain.factories.ProviderBackedOpenAIChatClient", _CapturingClient):
            classifier = build_classifier_from_snapshot(snapshot, Settings(_env_file=None))
            self.assertIsInstance(classifier, LlmConstrainedIntentClassifier)
            result = classifier.classify(
                ClassifierInput(
                    message="profile model route",
                    session_state={},
                    candidates=(),
                    allowed_actions=("CLARIFY",),
                    thresholds={"classifierMinConfidence": 0.6},
                )
            )

        payload = _CapturingClient.payloads[-1]
        self.assertTrue(result.used_real_llm)
        self.assertEqual(_CapturingClient.init_kwargs["timeout"], 7)
        self.assertEqual(_CapturingClient.init_kwargs["max_attempts"], 2)
        self.assertEqual(_CapturingClient.init_kwargs["retry_sleep"], 0.1)
        self.assertEqual(payload["model"], "profile-classifier-model")
        self.assertEqual(payload["temperature"], 0.35)
        self.assertEqual(payload["max_tokens"], 123)
        self.assertIn("PROFILE PROMPT", payload["messages"][0]["content"])
        self.assertEqual(
            result.debug["usage"],
            {"inputTokens": 9, "outputTokens": 4, "totalTokens": 13, "estimated": False},
        )

    def test_fallback_factory_honors_fake_disabled_and_policy_attempts(self) -> None:
        snapshot = _snapshot()

        fake_agent = build_fallback_agent_from_snapshot(snapshot)
        policy = build_agent_output_policy_from_snapshot(snapshot)

        disabled_snapshot = _snapshot()
        disabled_snapshot["fallbackAgent"] = {
            **disabled_snapshot["fallbackAgent"],
            "enabled": False,
        }
        existing_agent_snapshot = _snapshot()
        existing_agent_snapshot["fallbackAgent"] = {
            **existing_agent_snapshot["fallbackAgent"],
            "type": "existing_agent",
            "agentId": 42,
        }

        self.assertIsInstance(fake_agent, FakeFallbackAgent)
        self.assertEqual(policy.max_clarification_attempts, 2)
        self.assertIsNone(build_fallback_agent_from_snapshot(disabled_snapshot))
        self.assertIsNone(build_fallback_agent_from_snapshot(existing_agent_snapshot, session=None))

    def test_fallback_factory_can_call_existing_agent_from_profile(self) -> None:
        with _agent_session() as session:
            agent_id = _seed_agent(session, system_prompt="You are the runtime-lab fallback Agent.")
            snapshot = _snapshot()
            snapshot["fallbackAgent"] = {
                **snapshot["fallbackAgent"],
                "type": "existing_agent",
                "agentId": agent_id,
            }

            agent = build_fallback_agent_from_snapshot(snapshot, session=session)
            self.assertIsNotNone(agent)
            output = agent.run(
                FallbackAgentRequest(
                    message="机场大巴末班车几点，航班延误还能赶上吗？",
                    active_task=None,
                    suspended_tasks=[],
                    recent_events=[],
                )
            )

        self.assertEqual(output.response_type, "answer")
        self.assertIn("LLM mock:", output.answer)
        self.assertIn("机场大巴", output.answer)
        self.assertNotIn("运行上下文", output.answer)
        self.assertNotIn("不要发起或修改 SOP", output.answer)
        self.assertGreaterEqual(output.confidence, 0.6)
        self.assertEqual(output.citations[0]["agentId"], agent_id)


class _CapturingClient:
    init_kwargs: dict[str, object] = {}
    payloads: list[dict[str, object]] = []

    def __init__(self, config: object, timeout: float, max_attempts: int, retry_sleep: float) -> None:
        self.config = config
        self.__class__.init_kwargs = {
            "timeout": timeout,
            "max_attempts": max_attempts,
            "retry_sleep": retry_sleep,
        }

    def complete(self, payload: dict[str, object]) -> dict[str, object]:
        self.__class__.payloads.append(payload)
        return {
            "choices": [
                {
                    "message": {
                        "content": json.dumps(
                            {
                                "selected_action": "CLARIFY",
                                "selected_candidate_id": None,
                                "confidence": 0.44,
                                "rationale": "profile prompt used",
                                "needs_clarification": True,
                                "clarification_question": "profile clarification",
                            }
                        )
                    }
                }
            ],
            "usage": {"prompt_tokens": 9, "completion_tokens": 4, "total_tokens": 13},
        }


def _snapshot() -> dict[str, object]:
    payload = _profile_payload("041.3 factories")
    return {
        "profileId": 1,
        "profileVersion": 1,
        "status": "active",
        "mode": payload["mode"],
        "bindings": payload["bindings"],
        "thresholds": payload["thresholds"],
        "classifier": payload["classifier"],
        "faq": payload["faq"],
        "rag": payload["rag"],
        "fallbackAgent": payload["fallbackAgent"],
        "handoff": payload["handoff"],
    }


@contextmanager
def _agent_session() -> Generator[Session, None, None]:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_policy_existing_agent.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_baseline_tables()
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        tmp_dir.cleanup()


def _seed_agent(session: Session, *, system_prompt: str) -> int:
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    provider_id = session.execute(
        provider.insert().values(
            name=f"Runtime Policy Factory Provider {time.time_ns()}",
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
            name="Runtime Policy Factory Model",
            model_id="runtime-policy-fallback-model",
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
            name=f"Runtime Policy Factory Agent {time.time_ns()}",
            description="",
            system_prompt=system_prompt,
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


if __name__ == "__main__":
    unittest.main()
