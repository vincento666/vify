import unittest
from typing import cast

from app.core.config import Settings
from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType
from app.modules.customer_assistant.domain.shadow import (
    CustomerAssistantShadowSettings,
    FakeCustomerAssistantShadowClient,
    ProviderBackedCustomerAssistantShadowClient,
    ShadowPhase,
    build_shadow_event_payload,
    parse_recommendation_shadow_output,
    parse_task_recognition_shadow_output,
)
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.provider.api.facade import ProviderModelFacade


class CustomerAssistantShadowTest(unittest.TestCase):
    def test_settings_fake_client_parser_and_event_payloads_are_deterministic(self) -> None:
        defaults = CustomerAssistantShadowSettings.from_settings(Settings())
        configured = CustomerAssistantShadowSettings.from_settings(
            Settings(
                customer_assistant_llm_shadow_mode="fake",
                customer_assistant_llm_shadow_model_config_id=17,
                customer_assistant_llm_shadow_task_recognition=False,
                customer_assistant_llm_shadow_recommendation=True,
            )
        )

        command = TaskCommand(
            TaskCommandType.ADD_TASK,
            task_key="refund_ticket:ORDER-100",
            task_type="refund_ticket",
            business_key="ORDER-100",
            worker_type="chatflow_sop",
            worker_ref="refund_ticket",
            reason="customer asked for refund",
        )
        client = FakeCustomerAssistantShadowClient()
        task_result = parse_task_recognition_shadow_output(
            client.recognize_tasks(message="refund ORDER-100", commands=[command])
        )
        recommendation_result = parse_recommendation_shadow_output(
            client.recommend(
                task_summaries=[{"taskKey": "refund_ticket:ORDER-100"}],
                operator_recommendation="Ask for ticket number.",
                customer_reply_draft="Could you provide the ticket number?",
            )
        )
        invalid_result = parse_task_recognition_shadow_output("{not-json")

        payload = build_shadow_event_payload(
            phase=ShadowPhase.TASK_RECOGNITION,
            mode=configured.mode,
            model_config_id=configured.model_config_id,
            actor="operator",
            baseline={"commands": [command.task_key]},
            shadow=task_result.data,
            diff={"matches": True, "differences": []},
            latency_ms=9,
            error=None,
        )

        self.assertEqual(defaults.mode, "off")
        self.assertTrue(defaults.task_recognition_enabled)
        self.assertTrue(defaults.recommendation_enabled)
        self.assertEqual(configured.mode, "fake")
        self.assertEqual(configured.model_config_id, 17)
        self.assertFalse(configured.task_recognition_enabled)
        self.assertTrue(task_result.ok)
        self.assertEqual(task_result.data["commands"][0]["taskKey"], "refund_ticket:ORDER-100")
        self.assertTrue(recommendation_result.ok)
        self.assertIn("operatorRecommendation", recommendation_result.data)
        self.assertFalse(invalid_result.ok)
        self.assertEqual(payload["phase"], "task_recognition")
        self.assertEqual(payload["mode"], "fake")
        self.assertEqual(payload["modelConfigId"], 17)
        self.assertEqual(payload["actor"], "operator")
        self.assertEqual(payload["latencyMs"], 9)

    def test_provider_backed_shadow_keeps_using_sync_complete_facade(self) -> None:
        client = _SyncFacadeRecordingClient()
        shadow = ProviderBackedCustomerAssistantShadowClient(
            cast(ProviderModelFacade, _ModelFacade()),
            model_config_id=17,
            llm_client_factory=lambda _config: client,  # type: ignore[arg-type]
        )
        command = TaskCommand(
            TaskCommandType.ADD_TASK,
            task_key="refund_ticket:ORDER-100",
            task_type="refund_ticket",
            business_key="ORDER-100",
            worker_type="chatflow_sop",
            worker_ref="refund_ticket",
            reason="customer asked for refund",
        )

        raw = shadow.recognize_tasks(message="refund ORDER-100", commands=[command])

        self.assertIn('"commands"', raw)
        self.assertEqual(client.complete_calls, 1)
        self.assertEqual(client.async_stream_calls, 0)


class _ModelFacade:
    def get_enabled_model_config(self, model_config_id: int) -> ModelConfigDto:
        return ModelConfigDto(
            id=model_config_id,
            provider_id=3,
            provider_type="OPENAI",
            provider_base_url="mock://customer-assistant-shadow",
            provider_auth_config={},
            name="shadow-test-model",
            model_id="shadow-test-model",
            context_size=2048,
            extra_params={},
        )


class _SyncFacadeRecordingClient:
    def __init__(self) -> None:
        self.complete_calls = 0
        self.async_stream_calls = 0

    def complete(self, _payload: dict[str, object]) -> dict[str, object]:
        self.complete_calls += 1
        return {
            "choices": [
                {
                    "message": {
                        "content": '{"commands": [], "confidence": 0, "warnings": []}',
                    }
                }
            ]
        }

    async def stream_complete_async(self, _payload: dict[str, object]) -> dict[str, object]:
        self.async_stream_calls += 1
        raise AssertionError("Customer Assistant shadow must keep using complete()")


if __name__ == "__main__":
    unittest.main()
