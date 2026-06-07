import time
import unittest
from collections.abc import Callable
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop import mock_sop_manifests
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


EXPECTED_SOP_IDS = (
    "refund_ticket",
    "change_flight",
    "invoice_apply",
    "baggage_service",
    "seat_checkin",
    "flight_status",
    "special_assistance",
    "pet_cabin",
    "irregular_flight",
    "membership_service",
)

REQUIRED_NODE_TYPES = {
    "LLM",
    "CONDITION",
    "INTENT_RECOGNITION",
    "VARIABLE_AGGREGATION",
    "QUESTION",
    "API_CALL",
    "VARIABLE_PARSE",
}

START_UTTERANCES: dict[str, tuple[str, ...]] = {
    "refund_ticket": (
        "您好，我临时出差取消了，想把今晚这张机票退掉，麻烦帮我看看退票规则",
        "我不飞了，票款能不能退回来？订单还在手机里",
        "家里有事，这趟航班想取消行程申请退费",
        "昨天订错了航班，我要退票，但想先知道扣费",
        "航班延误很久，我想走非自愿退票流程",
        "帮我处理退机票，最好保留短信通知",
        "这张票不需要了，我想退掉航班",
        "能不能帮我查下退票要扣多少，然后继续办理",
        "我买错日期，票款能退吗？想取消行程",
        "我要退票，乘机人是我本人，后面补订单信息",
    ),
    "change_flight": (
        "我明天会议提前，想把航班改签到更早一班",
        "这趟来不及赶到机场，帮我换个航班",
        "能不能改日期？我想从周五改到周六走",
        "我需要改签航班，最好还是同一家航空公司",
        "计划变了，想调整航班时间，不知道差价多少",
        "帮我改航班，订单稍后发你",
        "我想改签，原航班太晚了",
        "小孩同行，改时间时帮我保留邻座",
        "我需要换航班，别取消订单",
        "我要改签航班，优先同舱位",
    ),
    "invoice_apply": (
        "公司报销要凭证，帮我开一下电子发票",
        "我需要行程单和发票，抬头稍后给你",
        "能补开发票吗？这趟差旅财务催着要",
        "帮我申请发票，订单号等会发",
        "我想开票，税号在公司系统里我复制给你",
        "上周飞完了，现在需要报销凭证",
        "电子票据怎么下载？不行就帮我开票",
        "我要申请行程单，用于公司报销",
        "机票发票麻烦处理一下，抬头是企业",
        "我要开发票，先进入流程吧",
    ),
    "baggage_service": (
        "我带了两个箱子，想加购托运行李额",
        "行李可能超重，帮我看看能不能提前买",
        "我要办理行李服务，带一件运动器材",
        "托运行李额度不够，想补一点",
        "随身行李尺寸有点大，帮我确认托运方案",
        "我需要购买行李额，别到机场再排队",
        "行李服务帮我开一下，订单稍后给",
        "箱子大概二十八公斤，想提前处理超重",
        "我有婴儿车和箱子，问下行李怎么处理",
        "帮我办理加行李，越早越好",
    ),
    "seat_checkin": (
        "我想线上值机，最好选靠窗座位",
        "帮我选座，同行两个人想坐一起",
        "现在可以办理值机吗？我想要过道",
        "我需要登机牌，座位不要最后一排",
        "帮我值机选座，带老人尽量靠前",
        "我要选座，靠窗或安全出口都行",
        "线上值机失败了，你帮我走一下流程",
        "能不能帮我办登机牌？订单稍后发",
        "我想换座位，离同行人近一点",
        "我要值机选座，航班是明天早上",
    ),
    "flight_status": (
        "我想查一下今天航班动态，听说天气不好",
        "帮我看航班是不是延误了，机场通知不清楚",
        "我要查询航班状态，接人时间要安排",
        "航班动态能查吗？我怕登机口变了",
        "帮我看看起飞时间有没有调整",
        "这个航班有没有取消？我准备出门",
        "我需要实时航班状态，订单稍后给",
        "查一下到达时间，司机在等",
        "航班状态更新了吗？我没收到短信",
        "我要查航班动态，可能延误",
    ),
    "special_assistance": (
        "老人第一次坐飞机，需要轮椅协助",
        "我腿受伤了，想申请特殊旅客服务",
        "帮我预约轮椅，到机场有人接一下",
        "孕妇乘机需要什么协助？我想先登记",
        "老人行动不便，需要无障碍协助",
        "我要申请特殊服务，航班信息稍后发",
        "能安排轮椅和优先登机吗？",
        "我父亲需要特殊协助，麻烦开流程",
        "行动不便乘客怎么办理？",
        "申请轮椅服务，越详细越好",
    ),
    "pet_cabin": (
        "我想带猫坐飞机，问下宠物进客舱要求",
        "我要办理宠物托运，小狗证件都有",
        "宠物能不能随身带？需要什么材料",
        "帮我开宠物运输流程，航空箱已买",
        "我带一只猫，需要确认疫苗证明",
        "宠物托运怎么收费？我想办理",
        "小型犬能进客舱吗？先帮我看规则",
        "我要申请宠物服务，订单后面给",
        "猫咪托运需要提前多久预约？",
        "帮我办理宠物乘机，材料我可以补",
    ),
    "irregular_flight": (
        "航班取消了，我需要改签或补偿方案",
        "延误四小时，客服说可以非自愿处理",
        "我遇到不正常航班，想知道能不能改到明天",
        "航班备降了，后续住宿交通怎么安排",
        "机场通知航班取消，帮我走异常航班流程",
        "大面积延误，怎么处理签转？",
        "我需要不正常航班协助，订单稍后给",
        "航班取消后能免费退改吗？",
        "我被通知延误，想要保障方案",
        "异常航班怎么处理，麻烦帮我登记",
    ),
    "membership_service": (
        "我的会员里程没到账，帮我补登一下",
        "常旅客账号积分不对，想查明细",
        "我要处理会员服务，航段积分少了",
        "帮我补登里程，登机牌还在",
        "会员等级权益怎么没有生效？",
        "我想查积分和升舱券，订单稍后给",
        "常旅客号码填错了，能补录吗？",
        "里程补登需要什么材料？先帮我开流程",
        "会员积分没入账，麻烦处理",
        "我要办理会员里程服务",
    ),
}


class RuntimeLabAirlineScaleE2ETest(unittest.TestCase):
    def test_airline_sop_catalog_has_10_deep_node_designs(self) -> None:
        manifests = mock_sop_manifests()

        self.assertEqual(tuple(manifests), EXPECTED_SOP_IDS)
        node_types = {step.node_type for manifest in manifests.values() for step in manifest.steps}
        self.assertTrue(REQUIRED_NODE_TYPES.issubset(node_types), node_types)
        for sop_id, manifest in manifests.items():
            self.assertGreaterEqual(len(manifest.steps), 5, sop_id)
            self.assertGreaterEqual(len(manifest.trigger_keywords), 5, sop_id)
            self.assertGreaterEqual(len(manifest.strong_trigger_keywords), 3, sop_id)
            self.assertIn("collect_order_no", {step.step_id for step in manifest.steps})
            self.assertIn("confirm", {step.step_id for step in manifest.steps})

    def test_100_realistic_airline_turns_route_collect_and_complete(self) -> None:
        with TestClient(app) as client:
            executed = 0
            for sop_id, utterances in START_UTTERANCES.items():
                for index, utterance in enumerate(utterances):
                    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
                    started = _message(client, session_id, utterance)
                    collected = _message(
                        client,
                        session_id,
                        f"订单号 MU{sop_id[:2].upper()}{index:03d}，手机号 1380013{index:04d}，"
                        f"乘机人张测试，明天上午从北京出发，备注希望短信通知",
                    )
                    completed = _message(client, session_id, "确认，按这个方案办理")

                    self.assertEqual(started["routeDecision"]["action"], "START_SOP", utterance)
                    self.assertEqual(started["activeTask"]["sopId"], sop_id)
                    self.assertEqual(started["activeTask"]["currentStep"], "collect_order_no")
                    self.assertEqual(collected["routeDecision"]["action"], "CONTINUE_ACTIVE_SOP")
                    self.assertEqual(collected["activeTask"]["currentStep"], "confirm")
                    self.assertEqual(collected["activeTask"]["businessRefs"]["phone"], f"1380013{index:04d}")
                    self.assertTrue(collected["activeTask"]["businessRefs"]["order_no"].startswith("MU"))
                    self.assertEqual(completed["routeDecision"]["action"], "COMPLETE_TASK")
                    self.assertIsNone(completed["activeTask"])
                    executed += 1

            self.assertGreaterEqual(executed, 100)

    def test_switch_resume_matrix_covers_five_airline_jumps_with_single_suspended_boundary(self) -> None:
        jump_pairs = (
            ("refund_ticket", "flight_status"),
            ("change_flight", "special_assistance"),
            ("invoice_apply", "membership_service"),
            ("baggage_service", "pet_cabin"),
            ("seat_checkin", "irregular_flight"),
        )
        with TestClient(app) as client:
            for primary, secondary in jump_pairs:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
                primary_started = _message(client, session_id, START_UTTERANCES[primary][0])
                secondary_started = _message(client, session_id, START_UTTERANCES[secondary][0])
                _message(client, session_id, "订单号 CA8888，手机号 13800138888，乘机人李测试")
                secondary_done = _message(client, session_id, "确认办理")
                resumed = _message(client, session_id, f"继续处理{primary_started['activeTask']['sopId']}")
                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]

                self.assertEqual(secondary_started["routeDecision"]["action"], "SUSPEND_AND_START")
                self.assertEqual(secondary_started["activeTask"]["sopId"], secondary)
                self.assertEqual(secondary_done["resumeOffer"]["sopId"], primary)
                self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
                self.assertEqual(resumed["activeTask"]["sopId"], primary)
                self.assertLessEqual(len([task for task in tasks if task["status"] == "SUSPENDED"]), 1)

    def test_real_chatflow_bound_sop_still_routes_through_runtime_lab_control_plane(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_rich_chatflow_sop_fixture(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(
                int(cast(int | str, chatflow["id"]))
            )
            try:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
                started = _message(client, session_id, "我想退票，顺便确认一下非自愿政策")
                switched = _message(client, session_id, "先帮我开发票，公司报销急用")
                _message(client, session_id, "订单号 INV034，手机号 13800139999，抬头是测试科技")
                invoice_done = _message(client, session_id, "确认")
                resumed = _message(client, session_id, "继续处理退票")
                collected = _message(client, session_id, "订单号：MU034，手机号 13800130034，乘机人王测试")
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(started["activeTask"]["sopId"], "refund_ticket")
        self.assertEqual(started["activeTask"]["currentStep"], "info_order")
        self.assertIn("手机号", started["reply"])
        self.assertEqual(switched["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(invoice_done["resumeOffer"]["sopId"], "refund_ticket")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertEqual(collected["activeTask"]["currentStep"], "confirm_1")
        self.assertEqual(collected["activeTask"]["businessRefs"]["phone"], "13800130034")


def _runtime_service_override(chatflow_id: int) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_service = WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            chatflow_state_repository=ChatflowStateRepository(session),
        )
        adapter = ChatflowSopRuntimeAdapter(
            workflow_service,
            sop_chatflow_ids={"refund_ticket": chatflow_id},
            fallback_adapter=FakeSopRuntimeAdapter(),
        )
        return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)

    return override


def _message(client: TestClient, session_id: int, message: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _create_rich_chatflow_sop_fixture(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"034.4 Rich Airline SOP {stamp}",
            "description": "runtime-lab rich chatflow SOP fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "intent_1",
                    "type": "INTENT_RECOGNITION",
                    "name": "识别退票类型",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "intent",
                        "defaultIntent": "voluntary",
                        "classifierMode": "fake",
                        "intents": [
                            {"key": "involuntary", "name": "非自愿", "examples": ["延误", "取消", "非自愿"]},
                            {"key": "voluntary", "name": "自愿", "examples": ["退票", "取消行程"]},
                        ],
                    },
                },
                {
                    "nodeKey": "llm_1",
                    "type": "LLM",
                    "name": "政策说明",
                    "config": {
                        "prompt": "民航退票政策摘要: {{intent_1.intent}} {{start.sys.query}}",
                        "outputVariable": "policy",
                    },
                },
                {
                    "nodeKey": "info_order",
                    "type": "INFORMATION_COLLECTION",
                    "name": "收集订单和联系人",
                    "config": {
                        "inputSource": "{{start.sys.query}}",
                        "outputVariable": "contact",
                        "collectionKey": "contact",
                        "includeHistory": True,
                        "followupTemplate": "请补充订单号和手机号：{{missing}}",
                        "fields": [
                            {"name": "order_no", "type": "string", "required": True, "description": "订单号"},
                            {
                                "name": "phone",
                                "type": "string",
                                "required": True,
                                "description": "手机号",
                                "targetScope": "conversation",
                                "targetVariable": "phone",
                            },
                        ],
                    },
                },
                {
                    "nodeKey": "aggregate_1",
                    "type": "VARIABLE_AGGREGATION",
                    "name": "聚合上下文",
                    "config": {
                        "outputVariable": "summary",
                        "strategy": "concat",
                        "separator": "|",
                        "sources": [
                            {"name": "policy", "value": "{{llm_1.policy}}"},
                            {"name": "order", "value": "{{info_order.order_no}}"},
                            {"name": "phone", "value": "{{info_order.phone}}"},
                        ],
                    },
                },
                {
                    "nodeKey": "confirm_1",
                    "type": "QUESTION",
                    "name": "确认办理",
                    "config": {
                        "question": "已校验退票材料，请确认是否继续办理退票。",
                        "outputVariable": "confirm",
                    },
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {
                        "outputVariable": "final",
                        "output": "order={{info_order.order_no}} phone={{info_order.phone}} confirm={{confirm_1.answer}} summary={{aggregate_1.summary}}",
                    },
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "intent_1", "condition": None},
                {"sourceNodeKey": "intent_1", "targetNodeKey": "llm_1", "condition": None},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "info_order", "condition": None},
                {"sourceNodeKey": "info_order", "targetNodeKey": "aggregate_1", "condition": None},
                {"sourceNodeKey": "aggregate_1", "targetNodeKey": "confirm_1", "condition": None},
                {"sourceNodeKey": "confirm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


if __name__ == "__main__":
    unittest.main()
