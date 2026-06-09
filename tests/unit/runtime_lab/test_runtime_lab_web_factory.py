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

    def test_default_runtime_lab_faq_gate_answers_airline_faq_without_external_kb(self) -> None:
        from app.modules.runtime_lab.web.router import _runtime_lab_faq_answer_gate

        gate = _runtime_lab_faq_answer_gate(Settings(), None)

        self.assertIsNotNone(gate)
        assert gate is not None
        proposal = gate.propose("儿童票可以退吗？", active_task=None, suspended_tasks=[])
        self.assertIsNotNone(proposal)
        assert proposal is not None
        self.assertEqual(proposal.source_layer, "runtime_airline_faq")
        self.assertIn("儿童票", proposal.answer)

    def test_runtime_airline_faq_gate_does_not_steal_transactional_sop_request(self) -> None:
        from app.modules.runtime_lab.web.router import _runtime_lab_faq_answer_gate

        gate = _runtime_lab_faq_answer_gate(Settings(), None)

        self.assertIsNotNone(gate)
        assert gate is not None
        proposal = gate.propose("行李可能超重，能不能提前买一点额度", active_task=None, suspended_tasks=[])
        self.assertIsNone(proposal)
