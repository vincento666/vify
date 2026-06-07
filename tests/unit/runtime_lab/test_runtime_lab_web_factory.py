import unittest

from app.modules.runtime_lab.web.router import _runtime_lab_chatflow_bindings


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
