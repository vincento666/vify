import unittest

from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.domain.engine import ApiCallNodeExecutor, ConditionNodeExecutor
from tests.support.local_api import LocalApiServer


class WorkflowRuntimeParityTest(unittest.TestCase):
    def test_api_call_node_executes_real_local_http_request(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)
        context = ExecutionContext()
        context.set_output("start", {"token": "secret-token", "message": "hello api"})

        result = ApiCallNodeExecutor().execute(
            {
                "node_key": "api",
                "type": "API_CALL",
                "config": {
                    "method": "POST",
                    "endpoint": f"{server.url}/echo/{{{{start.message}}}}",
                    "headers": '[{"name": "X-Test-Token", "value": "{{start.token}}"}]',
                    "body": {"message": "{{start.message}}", "source": "workflow"},
                    "outputVariable": "response",
                },
            },
            context,
        )

        self.assertEqual(
            result,
            {
                "response": {
                    "ok": True,
                    "method": "POST",
                    "path": "/echo/hello%20api",
                    "token": "secret-token",
                    "body": {"message": "hello api", "source": "workflow"},
                }
            },
        )

    def test_condition_node_evaluates_coze_style_multi_condition_branches(self) -> None:
        context = ExecutionContext()
        context.set_output("start", {"vip": "gold", "intent": "refund billing", "amount": 120})

        result = ConditionNodeExecutor().execute(
            {
                "node_key": "router",
                "type": "CONDITION",
                "config": {
                    "outputVariable": "route",
                    "conditionBranches": [
                        {
                            "key": "vip_refund",
                            "logic": "AND",
                            "conditions": [
                                {"left": "{{start.vip}}", "operator": "equals", "right": "gold"},
                                {"left": "{{start.intent}}", "operator": "contains", "right": "refund"},
                                {"left": "{{start.amount}}", "operator": "greater_than", "right": "100"},
                            ],
                        },
                        {
                            "key": "billing",
                            "logic": "OR",
                            "conditions": [
                                {"left": "{{start.intent}}", "operator": "contains", "right": "invoice"},
                                {"left": "{{start.intent}}", "operator": "contains", "right": "receipt"},
                            ],
                        },
                    ],
                    "defaultBranch": "default",
                },
            },
            context,
        )

        self.assertEqual(result, {"route": "vip_refund"})

if __name__ == "__main__":
    unittest.main()
