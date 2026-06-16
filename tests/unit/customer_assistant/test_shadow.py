import unittest

from app.core.config import Settings
from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType
from app.modules.customer_assistant.domain.shadow import (
    CustomerAssistantShadowSettings,
    FakeCustomerAssistantShadowClient,
    ShadowPhase,
    build_shadow_event_payload,
    parse_recommendation_shadow_output,
    parse_task_recognition_shadow_output,
)


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


if __name__ == "__main__":
    unittest.main()
