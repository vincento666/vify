import time
import unittest
from typing import Any, cast

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.runtime_lab.domain.chatflow_adapter import (
    ChatflowSopRuntimeAdapter,
    _business_values_from_text,
    _collected,
    _runtime_input,
)
from app.modules.runtime_lab.domain.sop_adapter import SopExecutionRequest, SopExecutionStatus
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class ChatflowSopRuntimeAdapterIntegrationTest(unittest.TestCase):
    def test_start_continue_suspend_resume_and_complete_real_chatflow_sop(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, stamp)
            adapter = _adapter(int(cast(int | str, chatflow["id"])))

            started = adapter.start_sop(_request(message="我要退票", stamp=stamp))
            suspended = adapter.suspend_sop(_request(checkpoint=started.checkpoint, stamp=stamp))
            collected = adapter.continue_sop(
                _request(message="订单号：TK-100，手机号 13800138000", checkpoint=suspended, stamp=stamp)
            )
            completed = adapter.resume_sop(
                _request(message="确认", checkpoint=collected.checkpoint, stamp=stamp)
            )

        self.assertEqual(started.status, SopExecutionStatus.WAITING)
        self.assertEqual(started.current_step, "info_order")
        self.assertIn("phone", started.pending_prompt)
        self.assertEqual(suspended.current_step, "info_order")
        self.assertEqual(collected.status, SopExecutionStatus.WAITING)
        self.assertEqual(collected.current_step, "confirm_1")
        self.assertEqual(collected.collected["order_no"], "TK-100")
        self.assertEqual(collected.collected["phone"], "13800138000")
        self.assertEqual(completed.status, SopExecutionStatus.COMPLETED)
        self.assertEqual(completed.current_step, "completed")
        self.assertEqual(completed.collected["order_no"], "TK-100")
        self.assertEqual(completed.collected["phone"], "13800138000")

    def test_unknown_sop_returns_normalized_failure(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, time.time_ns())
            adapter = _adapter(int(cast(int | str, chatflow["id"])))

            result = adapter.start_sop(_request(sop_id="unknown_sop", message="start"))

        self.assertEqual(result.status, SopExecutionStatus.FAILED)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error["code"], "SOP_CHATFLOW_NOT_BOUND")

    def test_start_sop_normalizes_unexpected_chatflow_runtime_failure(self) -> None:
        adapter = ChatflowSopRuntimeAdapter(_FailingWorkflowService(), sop_chatflow_ids={"refund_ticket": 1})

        result = adapter.start_sop(_request(message="我要退票"))

        self.assertEqual(result.status, SopExecutionStatus.FAILED)
        self.assertIsNotNone(result.error)
        assert result.error is not None
        self.assertEqual(result.error["code"], "CHATFLOW_START_FAILED")
        self.assertIn("primary model rate limited", result.error["message"])

    def test_start_sop_passes_inherited_collected_values_to_chatflow(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, stamp)
            adapter = _adapter(int(cast(int | str, chatflow["id"])))

            started = adapter.start_sop(
                _request(
                    message="刚才那个订单我要继续处理",
                    collected={"order_no": "TK-100", "phone": "13800138000"},
                    stamp=stamp,
                )
            )

        self.assertEqual(started.status, SopExecutionStatus.WAITING)
        self.assertEqual(started.current_step, "confirm_1")
        self.assertEqual(started.collected["order_no"], "TK-100")
        self.assertEqual(started.collected["phone"], "13800138000")

    def test_chinese_booking_completion_reply_promotes_order_number(self) -> None:
        values = _business_values_from_text("已为您出票，订单编号：CA1301-20231027-8899，乘机人张三，手机号 13800138000。")

        self.assertEqual(values["order_no"], "CA1301-20231027-8899")
        self.assertEqual(values["passenger_name"], "张三")
        self.assertEqual(values["phone"], "13800138000")

    def test_booking_message_promotes_route_and_travel_time(self) -> None:
        values = _business_values_from_text("我要订一张明天上午9点从北京到广州的机票")

        self.assertEqual(values["origin"], "北京")
        self.assertEqual(values["destination"], "广州")
        self.assertEqual(values["route"], "北京到广州")
        self.assertEqual(values["travel_time"], "明天上午9点")

    def test_booking_message_uses_context_city_when_route_has_pronoun(self) -> None:
        values = _business_values_from_text("下周三上午要去上海开会，我想从广州飞过去")

        self.assertEqual(values["origin"], "广州")
        self.assertEqual(values["destination"], "上海")
        self.assertEqual(values["route"], "广州到上海")
        self.assertEqual(values["travel_time"], "下周三上午")

    def test_booking_message_does_not_treat_missing_passenger_notice_as_name(self) -> None:
        values = _business_values_from_text("下周三上午广州飞上海，先帮我订一张机票，乘机人和手机号我等下再给你")

        self.assertNotIn("passenger_name", values)
        self.assertEqual(values["route"], "广州到上海")
        self.assertEqual(values["travel_time"], "下周三上午")

    def test_passenger_name_strips_common_copula_prefix(self) -> None:
        values = _business_values_from_text("订票这边乘机人是李四，手机号13900001111")

        self.assertEqual(values["passenger_name"], "李四")
        self.assertEqual(values["phone"], "13900001111")

    def test_current_turn_slots_override_inherited_chatflow_session_variables(self) -> None:
        values = _collected(
            _request(message="订单号：MU034，手机号 13800130034，乘机人王测试"),
            output={"collected": {"phone": "13800139999"}},
            session_variables={"conversation": {"phone": "13800139999", "passenger_name": "旧乘机人"}},
        )

        self.assertEqual(values["phone"], "13800130034")
        self.assertEqual(values["passenger_name"], "王测试")
        self.assertEqual(values["order_no"], "MU034")

    def test_runtime_input_merges_current_turn_business_slots_with_inherited_context(self) -> None:
        runtime_input = _runtime_input(
            _request(
                message="我想把刚才这张票改签到后天上午",
                collected={
                    "order_no": "CA1301-20231027-8899",
                    "phone": "13800138000",
                    "passenger_name": "张三",
                },
            )
        )

        self.assertEqual(runtime_input["collected"]["order_no"], "CA1301-20231027-8899")
        self.assertEqual(runtime_input["collected"]["phone"], "13800138000")
        self.assertEqual(runtime_input["collected"]["passenger_name"], "张三")
        self.assertEqual(runtime_input["collected"]["target_time"], "后天上午")
        self.assertEqual(runtime_input["conversation.target_time"], "后天上午")

    def test_runtime_input_passes_runtime_lab_history_to_chatflow(self) -> None:
        history = [
            {"role": "user", "content": "我要订广州飞北京的航班，乘机人张三，手机号 13800138000"},
            {"role": "user", "content": "可以，帮我确认出票"},
        ]

        runtime_input = _runtime_input(_request(message="我要改签刚才那张机票", metadata={"history": history}))

        self.assertEqual(runtime_input["history"], history)

    def test_runtime_input_exposes_inherited_context_without_committing_slots(self) -> None:
        runtime_input = _runtime_input(
            _request(
                message="我要给另一个人改签机票",
                metadata={
                    "inheritedContext": {
                        "order_no": "CA1301-20231027-8899",
                        "phone": "13800138000",
                        "passenger_name": "张三",
                    }
                },
            )
        )

        self.assertNotIn("collected", runtime_input)
        self.assertNotIn("conversation", runtime_input)
        self.assertEqual(runtime_input["inherited_context"]["passenger_name"], "张三")

    def test_group_booking_confirm_with_missing_required_slots_stays_interruptible_collect(self) -> None:
        adapter = ChatflowSopRuntimeAdapter(
            _InterruptedConfirmWorkflowService(),
            sop_chatflow_ids={"group_booking": 1},
        )

        result = adapter.start_sop(
            _request(
                sop_id="group_booking",
                message="我们公司十几个人要去上海参会，先登记团队票，出发城市和时间我还没定",
            )
        )

        self.assertEqual(result.status, SopExecutionStatus.WAITING)
        self.assertEqual(result.current_step, "collect")
        self.assertIn("出发到达城市", result.pending_prompt)
        self.assertIn("出行时间", result.pending_prompt)
        self.assertNotIn("route", result.collected)
        self.assertNotIn("travel_time", result.collected)


def _adapter(chatflow_id: int) -> ChatflowSopRuntimeAdapter:
    session = get_session_factory()()
    service = WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        chatflow_state_repository=ChatflowStateRepository(session),
    )
    return ChatflowSopRuntimeAdapter(service, sop_chatflow_ids={"refund_ticket": chatflow_id})


class _FailingWorkflowService:
    def execute(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("primary model rate limited")


class _InterruptedConfirmWorkflowService:
    def execute(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        return {
            "status": "INTERRUPTED",
            "runId": 1,
            "sessionId": "",
            "output": {
                "interrupt": {"nodeKey": "confirm", "question": "是否提交团队询价？"},
                "collected": {"route": "上海", "travel_time": "未定", "passenger_count": "十几"},
            },
            "events": [{"type": "interrupt", "payload": {"nodeKey": "confirm"}, "id": 10, "checkpointId": 20}],
            "checkpointId": 20,
        }


def _request(
    message: str = "",
    checkpoint: Any | None = None,
    sop_id: str = "refund_ticket",
    collected: dict[str, Any] | None = None,
    metadata: dict[str, Any] | None = None,
    stamp: int | None = None,
) -> SopExecutionRequest:
    unique = stamp or time.time_ns()
    return SopExecutionRequest(
        runtime_session_id=1001,
        runtime_task_id=2002,
        sop_id=sop_id,
        message=message,
        checkpoint=checkpoint,
        collected=dict(collected or {}),
        business_refs=dict(collected or {}),
        metadata={
            "conversationId": f"runtime-lab-chatflow-{unique}",
            "userId": "runtime-lab-user",
            "channel": "runtime-lab",
            **(metadata or {}),
        },
    )


def _create_chatflow_sop_fixture(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"032 Runtime SOP {stamp}",
            "description": "test-only runtime adapter SOP fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "info_order",
                    "type": "INFORMATION_COLLECTION",
                    "name": "收集手机号",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "contact",
                        "collectionKey": "contact",
                        "fields": [
                            {
                                "name": "order_no",
                                "type": "string",
                                "required": True,
                                "description": "订单号",
                            },
                            {
                                "name": "phone",
                                "type": "string",
                                "required": True,
                                "description": "手机号",
                                "targetScope": "conversation",
                                "targetVariable": "phone",
                            }
                        ],
                    },
                },
                {
                    "nodeKey": "confirm_1",
                    "type": "QUESTION",
                    "name": "确认办理",
                    "config": {
                        "question": "请确认是否继续办理退票。",
                        "outputVariable": "confirm",
                        "answerType": "text",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "order={{info_order.order_no}} phone={{info_order.phone}} confirm={{confirm_1.answer}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_order", "condition": None},
                {"sourceNodeKey": "info_order", "targetNodeKey": "confirm_1", "condition": None},
                {"sourceNodeKey": "confirm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, object], data)
