import unittest

from app.core.config import Settings
from app.modules.customer_assistant.domain.llm_primary import (
    CustomerAssistantLlmRuntimeMode,
    CustomerAssistantLlmRuntimeSettings,
)


class CustomerAssistantLlmPrimarySettingsTest(unittest.TestCase):
    def test_runtime_mode_settings_default_primary_and_invalid_mode_falls_back_to_deterministic(self) -> None:
        defaults = CustomerAssistantLlmRuntimeSettings.from_settings(Settings())
        invalid = CustomerAssistantLlmRuntimeSettings.from_settings(
            Settings(customer_assistant_llm_runtime_mode="agentic_everything")
        )
        primary = CustomerAssistantLlmRuntimeSettings.from_settings(
            Settings(
                customer_assistant_llm_runtime_mode="llm_primary_with_fallback",
                customer_assistant_llm_primary_model_config_id=7,
                customer_assistant_llm_primary_min_confidence=0.91,
            )
        )

        self.assertEqual(defaults.mode, CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK)
        self.assertEqual(invalid.mode, CustomerAssistantLlmRuntimeMode.DETERMINISTIC)
        self.assertEqual(primary.mode, CustomerAssistantLlmRuntimeMode.LLM_PRIMARY_WITH_FALLBACK)
        self.assertEqual(primary.model_config_id, 7)
        self.assertEqual(primary.min_confidence, 0.91)


if __name__ == "__main__":
    unittest.main()
