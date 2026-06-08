import unittest

from app.core.config import Settings
from app.modules.runtime_lab.domain.classifier import LlmConstrainedIntentClassifier
from app.modules.runtime_lab.web.router import _runtime_lab_chatflow_bindings, _runtime_lab_intent_classifier


class RuntimeLabWebFactoryTest(unittest.TestCase):
    def test_parses_json_chatflow_bindings(self) -> None:
        bindings = _runtime_lab_chatflow_bindings('{"refund_ticket": 12, "invoice_apply": "34"}')

        self.assertEqual(bindings, {"refund_ticket": 12, "invoice_apply": 34})

    def test_parses_comma_chatflow_bindings(self) -> None:
        bindings = _runtime_lab_chatflow_bindings("refund_ticket:12,invoice_apply:34")

        self.assertEqual(bindings, {"refund_ticket": 12, "invoice_apply": 34})

    def test_parses_shell_unquoted_braced_chatflow_bindings(self) -> None:
        bindings = _runtime_lab_chatflow_bindings("{refund_ticket:12,invoice_apply:34}")

        self.assertEqual(bindings, {"refund_ticket": 12, "invoice_apply": 34})

    def test_empty_chatflow_bindings_disable_adapter_bridge(self) -> None:
        self.assertEqual(_runtime_lab_chatflow_bindings(None), {})
        self.assertEqual(_runtime_lab_chatflow_bindings(""), {})

    def test_default_intent_arbitrator_mode_uses_fake_classifier(self) -> None:
        self.assertIsNone(_runtime_lab_intent_classifier(Settings()))

    def test_llm_intent_arbitrator_mode_builds_real_llm_classifier(self) -> None:
        classifier = _runtime_lab_intent_classifier(
            Settings(
                runtime_lab_intent_arbitrator_mode="llm",
                runtime_lab_intent_arbitrator_base_url="https://openrouter.ai/api/v1",
                runtime_lab_intent_arbitrator_api_key="sk-test",
                runtime_lab_intent_arbitrator_model="test/model",
            )
        )

        self.assertIsInstance(classifier, LlmConstrainedIntentClassifier)
