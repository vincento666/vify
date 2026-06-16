import os
import unittest

from app.core.config import Settings
from app.modules.customer_assistant.domain.shadow import CustomerAssistantShadowSettings


@unittest.skipUnless(
    os.getenv("HIFY_CUSTOMER_ASSISTANT_LIVE_SHADOW_UAT") == "1",
    "live customer-assistant LLM shadow UAT is opt-in",
)
class CustomerAssistantLiveShadowUatTest(unittest.TestCase):
    def test_live_shadow_requires_model_config_id(self) -> None:
        settings = CustomerAssistantShadowSettings.from_settings(Settings())

        self.assertEqual(settings.mode, "live")
        self.assertIsNotNone(settings.model_config_id)


if __name__ == "__main__":
    unittest.main()
