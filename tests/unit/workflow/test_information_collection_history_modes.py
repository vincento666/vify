import unittest

from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.domain.engine import InformationCollectionNodeExecutor, WorkflowInterrupt


class InformationCollectionHistoryModeTest(unittest.TestCase):
    def test_current_turn_only_field_does_not_leak_from_history(self) -> None:
        context = _context(
            current_message="名字等信息是一样的",
            history_message="我要订广州飞北京的航班，明天上午走，乘机人张三，手机号 13800138000",
        )
        executor = InformationCollectionNodeExecutor(_HistoryLeakCompleter())

        with self.assertRaises(WorkflowInterrupt) as raised:
            executor.execute(_node(), context)

        output = raised.exception.output
        self.assertNotIn("target_time", output["collected"])
        self.assertEqual(output["missing"], ["target_time"])
        self.assertIn("当前只差期望改签时间", output["followup"])

    def test_current_turn_only_field_still_extracts_from_current_message(self) -> None:
        context = _context(
            current_message="改到后天上午",
            history_message="我要订广州飞北京的航班，明天上午走，乘机人张三，手机号 13800138000",
        )
        executor = InformationCollectionNodeExecutor(_HistoryLeakCompleter())

        output = executor.execute(_node(), context)

        self.assertTrue(output["complete"])
        self.assertEqual(output["collected"]["target_time"], "后天上午")

    def test_llm_extractor_error_falls_back_to_rule_extraction(self) -> None:
        context = ExecutionContext()
        context.set_output("start", {"sys.query": "目的城市:上海 预算金额:5000"})
        executor = InformationCollectionNodeExecutor(_FailingCompleter())

        output = executor.execute(
            {
                "node_key": "collect",
                "type": "INFORMATION_COLLECTION",
                "config": {
                    "inputSource": "{{start.sys.query}}",
                    "collectionKey": "travel",
                    "outputVariable": "travel",
                    "extractorMode": "llm",
                    "fields": [
                        {"name": "destination", "type": "string", "required": True, "description": "目的城市"},
                        {"name": "budget", "type": "string", "required": True, "description": "预算金额"},
                    ],
                },
            },
            context,
        )

        self.assertTrue(output["complete"])
        self.assertEqual(output["collected"], {"destination": "上海", "budget": "5000"})


def _context(*, current_message: str, history_message: str) -> ExecutionContext:
    context = ExecutionContext()
    context.set_output(
        "start",
        {
            "sys.query": current_message,
            "history": [{"role": "user", "content": history_message}],
            "collected": {
                "order_no": "CA1301-20231027-8899",
                "phone": "13800138000",
                "passenger_name": "张三",
            },
        },
    )
    return context


def _node() -> dict[str, object]:
    return {
        "node_key": "collect",
        "type": "INFORMATION_COLLECTION",
        "config": {
            "inputSource": "{{start.sys.query}}",
            "collectionKey": "info",
            "outputVariable": "info",
            "extractorMode": "llm",
            "includeHistory": True,
            "followupTemplate": "我先帮你看改签方案。{{collected_notice}}当前只差{{missing_labels}}。",
            "fields": [
                {"name": "order_no", "type": "string", "required": True, "description": "订单号"},
                {"name": "phone", "type": "string", "required": True, "description": "手机号"},
                {"name": "passenger_name", "type": "string", "required": True, "description": "乘机人姓名"},
                {
                    "name": "target_time",
                    "type": "string",
                    "required": True,
                    "description": "期望改签时间",
                    "historyMode": "current_turn_only",
                },
            ],
        },
    }


class _HistoryLeakCompleter:
    def complete_prompt(self, prompt: str, _options: dict[str, object] | None = None) -> str:
        if "改到后天上午" in prompt:
            return '{"target_time": "后天上午"}'
        if "明天上午" in prompt and "名字等信息是一样的" in prompt:
            return '{"target_time": "明天上午"}'
        return "{}"

    def supports_tool_calls(self) -> bool:
        return False


class _FailingCompleter:
    def complete_prompt(self, _prompt: str, _options: dict[str, object] | None = None) -> str:
        raise RuntimeError("provider unavailable")

    def supports_tool_calls(self) -> bool:
        return False
