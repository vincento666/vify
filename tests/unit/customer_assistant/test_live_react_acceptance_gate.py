import importlib
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


class CustomerAssistantLiveReactAcceptanceGateTest(unittest.TestCase):
    def test_default_ci_path_skips_and_writes_redacted_artifact(self) -> None:
        module = _load_gate_module(self)
        with tempfile.TemporaryDirectory() as tmp:
            result = module.run_customer_assistant_live_react_acceptance(env={}, output_dir=Path(tmp))

            artifact = Path(tmp) / "customer-assistant-live-react-acceptance-skipped.md"

            self.assertEqual(result.status, "skipped")
            self.assertEqual(result.live_model_calls, 0)
            self.assertTrue(artifact.exists())
            content = artifact.read_text(encoding="utf-8")
            self.assertIn("customer-assistant-live-react-acceptance", content)
            self.assertIn("skipped", content)
            self.assertNotIn("unit-api-key", content)

    def test_config_uses_required_default_model_pool_and_openai_compatible_provider(self) -> None:
        module = _load_gate_module(self)

        config = module.load_live_react_acceptance_config(
            {
                module.LIVE_GATE_FLAG: "1",
                "OPENROUTER_API_KEY": "unit-api-key",
            }
        )

        self.assertTrue(config.enabled)
        self.assertEqual(
            config.model_pool,
            ("xiaomi/mimo-v2-flash", "qwen/qwen3.5-9b", "deepseek/deepseek-v4-flash"),
        )
        self.assertEqual(config.provider_type, "OPENAI_COMPATIBLE")
        self.assertEqual(config.base_url, "https://openrouter.ai/api/v1")

    def test_customer_assistant_env_overrides_provider_key_base_url_and_model_pool(self) -> None:
        module = _load_gate_module(self)

        config = module.load_live_react_acceptance_config(
            {
                module.LIVE_GATE_FLAG: "1",
                "OPENROUTER_API_KEY": "openrouter-api-key",
                "HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY": "hify-api-key",
                "OPENROUTER_BASE_URL": "https://openrouter.example/api/v1",
                "HIFY_CUSTOMER_ASSISTANT_LIVE_BASE_URL": "https://compatible.example/api/v1/",
                "HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_POOL": "model-a, model-b",
            }
        )

        self.assertEqual(config.api_key, "hify-api-key")
        self.assertEqual(config.base_url, "https://compatible.example/api/v1")
        self.assertEqual(config.model_pool, ("model-a", "model-b"))

    def test_explicit_empty_env_does_not_fall_back_to_process_environment(self) -> None:
        module = _load_gate_module(self)

        with patch.dict(
            os.environ,
            {
                module.LIVE_GATE_FLAG: "1",
                "OPENROUTER_API_KEY": "host-api-key-should-not-be-used",
            },
            clear=True,
        ):
            config = module.load_live_react_acceptance_config(env={})

        self.assertFalse(config.enabled)
        self.assertEqual(config.api_key, "")

    def test_enabled_gate_fails_when_runner_omits_required_categories(self) -> None:
        module = _load_gate_module(self)

        def fake_runner(config):
            self.assertEqual(config.api_key, "unit-api-key")
            return module.LiveAcceptanceResult(
                status="completed",
                live_model_calls=3,
                categories=[
                    module.LiveCategoryResult(
                        name="task_recognition_accuracy",
                        status="passed",
                        success_model="xiaomi/mimo-v2-flash",
                        attempts=[{"model": "xiaomi/mimo-v2-flash", "status": "passed", "error": ""}],
                        summary="baggage_qa selected",
                    )
                ],
            )

        with tempfile.TemporaryDirectory() as tmp:
            result = module.run_customer_assistant_live_react_acceptance(
                env={module.LIVE_GATE_FLAG: "1", "OPENROUTER_API_KEY": "unit-api-key"},
                output_dir=Path(tmp),
                live_runner=fake_runner,
            )

            artifact = Path(result.evidence_path or "")

            self.assertEqual(result.status, "failed")
            self.assertEqual(result.live_model_calls, 3)
            self.assertIn("missing", result.reason.lower())
            self.assertTrue(artifact.exists())
            content = artifact.read_text(encoding="utf-8")
            self.assertIn("task_recognition_accuracy", content)
            self.assertIn("xiaomi/mimo-v2-flash", content)
            self.assertNotIn("unit-api-key", content)

    def test_enabled_gate_requires_proposed_action_safety_boundary_category(self) -> None:
        module = _load_gate_module(self)

        def fake_runner(config):
            self.assertEqual(config.api_key, "unit-api-key")
            return module.LiveAcceptanceResult(
                status="completed",
                live_model_calls=5,
                categories=[
                    module.LiveCategoryResult(
                        name="task_recognition_accuracy",
                        status="passed",
                        success_model="xiaomi/mimo-v2-flash",
                        attempts=[
                            {
                                "phase": "task_recognition",
                                "model": "xiaomi/mimo-v2-flash",
                                "status": "passed",
                            }
                        ],
                    ),
                    module.LiveCategoryResult(
                        name="two_stage_recommendation_quality",
                        status="passed",
                        success_model="qwen/qwen3.5-9b",
                        attempts=[
                            {
                                "phase": "two_stage_final",
                                "model": "qwen/qwen3.5-9b",
                                "status": "passed",
                            }
                        ],
                    ),
                    module.LiveCategoryResult(
                        name="react_worker_tool_call_policy_and_event_echo",
                        status="passed",
                        success_model="deepseek/deepseek-v4-flash",
                        attempts=[
                            {
                                "phase": "react_submit_refund",
                                "model": "deepseek/deepseek-v4-flash",
                                "status": "passed",
                            }
                        ],
                    ),
                ],
            )

        with tempfile.TemporaryDirectory() as tmp:
            result = module.run_customer_assistant_live_react_acceptance(
                env={module.LIVE_GATE_FLAG: "1", "OPENROUTER_API_KEY": "unit-api-key"},
                output_dir=Path(tmp),
                live_runner=fake_runner,
            )

        self.assertEqual(result.status, "failed")
        self.assertIn("proposed_action_safety_boundaries", result.reason)

    def test_enabled_gate_records_all_required_category_attempts_without_persisting_secret_values(self) -> None:
        module = _load_gate_module(self)

        def fake_runner(config):
            self.assertEqual(config.api_key, "unit-api-key")
            return module.LiveAcceptanceResult(
                status="completed",
                live_model_calls=4,
                categories=[
                    module.LiveCategoryResult(
                        name="task_recognition_accuracy",
                        status="passed",
                        success_model="xiaomi/mimo-v2-flash",
                        attempts=[{"model": "xiaomi/mimo-v2-flash", "status": "passed", "error": ""}],
                        summary="baggage_qa selected",
                    ),
                    module.LiveCategoryResult(
                        name="two_stage_recommendation_quality",
                        status="passed",
                        success_model="qwen/qwen3.5-9b",
                        attempts=[{"model": "qwen/qwen3.5-9b", "status": "passed", "error": ""}],
                        summary="two-stage selected",
                    ),
                    module.LiveCategoryResult(
                        name="react_worker_tool_call_policy_and_event_echo",
                        status="passed",
                        success_model="deepseek/deepseek-v4-flash",
                        attempts=[{"model": "deepseek/deepseek-v4-flash", "status": "passed", "error": ""}],
                        summary="tool call and event echo passed",
                    ),
                    module.LiveCategoryResult(
                        name="proposed_action_safety_boundaries",
                        status="passed",
                        success_model="deepseek/deepseek-v4-flash",
                        attempts=[
                            {
                                "model": "deepseek/deepseek-v4-flash",
                                "status": "passed",
                                "error": "",
                            }
                        ],
                        summary="pending proposed action",
                        evidence={
                            "actionStatus": "PENDING",
                            "actionType": "submit_refund",
                            "writeToolExecutions": 0,
                        },
                    ),
                ],
            )

        with tempfile.TemporaryDirectory() as tmp:
            result = module.run_customer_assistant_live_react_acceptance(
                env={module.LIVE_GATE_FLAG: "1", "OPENROUTER_API_KEY": "unit-api-key"},
                output_dir=Path(tmp),
                live_runner=fake_runner,
            )

            artifact = Path(result.evidence_path or "")

            self.assertEqual(result.status, "completed")
            self.assertEqual(result.live_model_calls, 4)
            self.assertTrue(artifact.exists())
            content = artifact.read_text(encoding="utf-8")
            self.assertIn("task_recognition_accuracy", content)
            self.assertIn("two_stage_recommendation_quality", content)
            self.assertIn("react_worker_tool_call_policy_and_event_echo", content)
            self.assertIn("proposed_action_safety_boundaries", content)
            self.assertNotIn("unit-api-key", content)


def _load_gate_module(test_case: unittest.TestCase):
    module_name = "app.modules.customer_assistant.eval.live_react_acceptance"
    spec = importlib.util.find_spec(module_name)
    test_case.assertIsNotNone(spec, f"{module_name} must exist")
    return importlib.import_module(module_name)


if __name__ == "__main__":
    unittest.main()
