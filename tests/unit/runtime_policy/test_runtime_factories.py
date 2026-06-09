import json
import unittest
from unittest.mock import patch

from app.core.config import Settings
from app.modules.runtime_lab.domain.agent_fallback import FakeFallbackAgent
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
        self.assertIsNone(build_fallback_agent_from_snapshot(existing_agent_snapshot))


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
            "usage": {"total_tokens": 1},
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


if __name__ == "__main__":
    unittest.main()
