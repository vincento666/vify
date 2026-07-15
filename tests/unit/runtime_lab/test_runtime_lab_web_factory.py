import unittest
from unittest.mock import patch

from app.core.config import Settings
from app.core.schema import register_baseline_tables
from app.modules.runtime_lab.domain.classifier import LlmConstrainedIntentClassifier
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.runtime_lab.web.router import (
    _runtime_lab_chatflow_bindings,
    _runtime_lab_intent_classifier,
    get_runtime_lab_service,
)
from tests.support.mysql import mysql8_session


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

    def test_empty_chatflow_bindings_production_bootstrap_does_not_use_fake_adapter(self) -> None:
        with mysql8_session("runtime_lab_web_factory_no_binding", register=register_baseline_tables) as session:
            with (
                patch(
                    "app.modules.runtime_lab.web.router.get_settings",
                    return_value=Settings(runtime_lab_sop_chatflow_ids=""),
                ),
                patch(
                    "app.modules.runtime_lab.web.router.RuntimePolicyResolver.resolve",
                    return_value={"policySnapshot": {}},
                ),
            ):
                service = get_runtime_lab_service(session)

        self.assertNotIsInstance(service._adapter, FakeSopRuntimeAdapter)

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

    def test_chatflow_sop_binding_wires_runtime_v2_service_by_default(self) -> None:
        with mysql8_session("runtime_lab_web_factory", register=register_baseline_tables) as session:
            with (
                patch(
                    "app.modules.runtime_lab.web.router.get_settings",
                    return_value=Settings(runtime_lab_sop_chatflow_ids="refund_ticket:42"),
                ),
                patch(
                    "app.modules.runtime_lab.web.router.RuntimePolicyResolver.resolve",
                    return_value={"policySnapshot": {}},
                ),
            ):
                service = get_runtime_lab_service(session)

        adapter = service._adapter
        self.assertIsInstance(adapter._runtime_v2_service, ChatflowRuntimeV2Service)
        self.assertIsNone(adapter._fallback_adapter)
        self.assertFalse(adapter._fallback_on_missing_chatflow)

    def test_mock_sop_llm_mode_does_not_wire_runtime_v2_live_llm_resolver(self) -> None:
        with mysql8_session("runtime_lab_web_factory_fake_v2_llm", register=register_baseline_tables) as session:
            with (
                patch(
                    "app.modules.runtime_lab.web.router.get_settings",
                    return_value=Settings(
                        runtime_lab_sop_chatflow_ids="refund_ticket:42",
                        runtime_lab_intent_arbitrator_mode="fake",
                    ),
                ),
                patch(
                    "app.modules.runtime_lab.web.router.RuntimePolicyResolver.resolve",
                    return_value={"policySnapshot": {}},
                ),
            ):
                service = get_runtime_lab_service(session)
                resolver = service._adapter._runtime_v2_service._llm_completer_resolver

        self.assertIsNone(resolver)

    def test_live_sop_llm_mode_wires_runtime_v2_live_llm_resolver(self) -> None:
        with mysql8_session("runtime_lab_web_factory_live_v2_llm", register=register_baseline_tables) as session:
            with (
                patch(
                    "app.modules.runtime_lab.web.router.get_settings",
                    return_value=Settings(
                        runtime_lab_sop_chatflow_ids="refund_ticket:42",
                        runtime_lab_sop_llm_mode="live",
                    ),
                ),
                patch(
                    "app.modules.runtime_lab.web.router.RuntimePolicyResolver.resolve",
                    return_value={"policySnapshot": {}},
                ),
            ):
                service = get_runtime_lab_service(session)
                resolver = service._adapter._runtime_v2_service._llm_completer_resolver

        self.assertIsNotNone(resolver)

    def test_chatflow_sop_binding_wires_runtime_invocation_mode_from_settings(self) -> None:
        with mysql8_session("runtime_lab_web_factory_mode", register=register_baseline_tables) as session:
            with (
                patch(
                    "app.modules.runtime_lab.web.router.get_settings",
                    return_value=Settings(
                        runtime_lab_sop_chatflow_ids="refund_ticket:42",
                        runtime_lab_sop_runtime_invocation_mode="async",
                    ),
                ),
                patch(
                    "app.modules.runtime_lab.web.router.RuntimePolicyResolver.resolve",
                    return_value={"policySnapshot": {}},
                ),
            ):
                service = get_runtime_lab_service(session)

        adapter = service._adapter
        self.assertEqual(adapter._runtime_invocation_mode, "async")

    def test_chatflow_sop_binding_defaults_to_async_background_invocation(self) -> None:
        with mysql8_session("runtime_lab_web_factory_default_async", register=register_baseline_tables) as session:
            with (
                patch(
                    "app.modules.runtime_lab.web.router.get_settings",
                    return_value=Settings(runtime_lab_sop_chatflow_ids="refund_ticket:42"),
                ),
                patch(
                    "app.modules.runtime_lab.web.router.RuntimePolicyResolver.resolve",
                    return_value={"policySnapshot": {}},
                ),
            ):
                service = get_runtime_lab_service(session)

        adapter = service._adapter
        self.assertEqual(adapter._runtime_invocation_mode, "async")
        self.assertIsNotNone(adapter._runtime_invocation_gateway._enqueue_background_run)
        self.assertTrue(adapter._runtime_invocation_gateway.supports_async_resume)
