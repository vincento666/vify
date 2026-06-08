from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import time
import unittest
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.agent.infra.repository import AgentRepository
from app.modules.chat.domain.llm_request import ProviderBackedOpenAIChatClient, ProviderChatConfig
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from tests.acceptance.test_runtime_lab_live_chatflow_llm_sop import (
    LiveSopCase,
    _assert_active,
    _create_live_chatflow_sop,
    _message,
    _seed_default_live_agent,
)
from tests.acceptance.test_runtime_lab_live_openrouter_full_chain import (
    DEFAULT_ARBITRATOR_MODEL,
    DEFAULT_HIGH_INTELLIGENCE_MODEL,
    _SingleOpenRouterModelClassifier,
    _assert_live_arbitrator,
    _assert_live_sop_llm_reply,
    _live_single_model_classifier,
)

RUN_LIVE = os.getenv("HIFY_RUN_LIVE_RUNTIME_LAB_QWEN_CORE_AIRLINE") == "1"
ARTIFACT_PATH = Path(
    "artifacts/slices/034-unified-routing-chat-lab/034.12/qwen-core-airline-live.md"
)


@dataclass(frozen=True)
class CoreScenario:
    business_area: str
    primary_sop_id: str
    primary_utterance: str
    secondary_sop_id: str
    secondary_utterance: str
    tertiary_sop_id: str
    tertiary_utterance: str


CORE_SOPS: dict[str, LiveSopCase] = {
    "flight_booking": LiveSopCase(
        "flight_booking",
        "机票预订",
        "下周去上海的行程想先看看可售航班，合适就出票",
        "刚才订航班那件事继续吧",
        "13910001001",
    ),
    "refund_ticket": LiveSopCase(
        "refund_ticket",
        "退票",
        "临时会议取消，明天那段不飞了，票款想处理回来",
        "刚才票款那件事继续吧",
        "13910001002",
    ),
    "change_flight": LiveSopCase(
        "change_flight",
        "改签",
        "原来的落地时间赶不上会议，想把航班改时间",
        "刚才改时间那件事继续吧",
        "13910001003",
    ),
    "flight_status": LiveSopCase(
        "flight_status",
        "航班动态",
        "我去机场接人，想确认那班实际到达时间和登机口",
        "刚才起飞时间那件事继续吧",
        "13910001004",
    ),
}


CORE_START_UTTERANCES: dict[str, tuple[str, ...]] = {
    "flight_booking": (
        "周五早上从北京去深圳，差旅审批说需要出票，想先看可售航班",
        "家里人临时要去成都，我想比较一下明晚买机票的航班",
        "下周一上海开会，麻烦帮我把北京过去需要出票的航班梳理一下",
        "客户把行程定下来了，我需要安排广州出发的机票销售流程",
        "月底去杭州参加培训，想确认还有没有可售航班，需要出票",
        "下午突然要飞厦门，能帮我看下现在需要出票的航班吗",
        "公司差旅要走机票销售，南京到重庆那段先帮我核一下",
        "我准备带孩子去三亚，想先把买机票的航班和乘机人信息整理好",
        "明天去西安的行程定下来了，需要出票，想从可售航班里挑一个合适的",
        "这趟差旅需要出票，但我还没确定哪个可售航班更稳妥",
    ),
    "refund_ticket": (
        "临时被通知会议取消，明天那段不飞了，票款想处理回来",
        "家里有急事无法成行，之前那张票的票款退回来规则帮我看一下",
        "计划变化后我不想去了，票款还能拿回来多少",
        "行程取消得比较突然，想把这张票退掉但担心扣费",
        "客户那边改成线上会议了，机票这边不飞了要处理票款",
        "我身体不太舒服，后天那班不飞了，票款退回来要怎么走",
        "签证没下来，这段取消行程，票款处理需要哪些材料",
        "刚收到通知出差取消了，之前扣费的票款能不能退回来",
        "计划取消行程了，麻烦看下票款怎么处理",
        "这趟不飞了，但我不清楚票款和手续费怎么计算",
    ),
    "change_flight": (
        "原来的落地安排赶不上会议，需要改签到晚一点",
        "客户把会议提前了，我那张票需要调整航班",
        "明天早班太赶，看看能不能改日期或者晚一点出发",
        "同行人改了计划，我也想改签到同一天晚些时候",
        "天气原因我想避开晚上那班，能不能换个航班",
        "酒店那边入住时间变了，机票改时间要怎么处理",
        "我现在这班转机太紧，想看看同舱位能否调整航班",
        "会议顺延一天，原来那张票需要改日期",
        "孩子放学后才来得及出发，想把票改签到晚一点",
        "上午安排取消了，原来的票想改时间到下午走",
    ),
    "flight_status": (
        "我去机场接人，想确认那班实际到达时间和登机口",
        "同事说天气不好，我想查一下航班状态是不是延误",
        "家人已经出发去机场了，能帮我看下起飞时间有没有变化吗",
        "我手里只有航班号，想知道今天到底几点到达时间",
        "司机在等客人，麻烦确认一下登机口和预计落地时间",
        "听说机场流控，帮我看下这班是否延误",
        "孩子第一次自己坐飞机，我想盯一下航班动态",
        "接机牌已经做好了，想确认航班状态有没有取消",
        "客户航班快到了吗，我需要知道准确到达时间",
        "登机口是不是变了，麻烦帮我查一下当前航班状态",
    ),
}

CORE_ORDER = ("flight_booking", "refund_ticket", "change_flight", "flight_status")


class RuntimeLabCoreAirlineMixedRoutingContractTest(unittest.TestCase):
    def test_forty_natural_core_airline_scenarios_cover_strong_keyword_routes_and_completion(self) -> None:
        initialise_database()
        register_baseline_tables()
        scenarios = _core_scenarios()

        self.assertEqual(len(scenarios), 40)
        self.assertGreaterEqual(_average_words(scenarios), 5)
        self.assertFalse(any(_looks_like_direct_keyword(scenario.primary_utterance) for scenario in scenarios))

        with TestClient(app) as client:
            results = [_run_single_sop_contract(client, index, scenario) for index, scenario in enumerate(scenarios)]

        self.assertEqual(len(results), 40)
        self.assertEqual({item["completedSops"] for item in results}, {1})
        self.assertGreaterEqual(
            sum(1 for item in results if item["startPolicyStage"] == "pre_classifier"),
            32,
        )


@unittest.skipUnless(
    RUN_LIVE,
    "Set HIFY_RUN_LIVE_RUNTIME_LAB_QWEN_CORE_AIRLINE=1 and OPENROUTER_API_KEY to run qwen core airline live acceptance",
)
class RuntimeLabLiveQwenCoreAirlineScenariosTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.arbitrator_model = os.getenv("HIFY_OPENROUTER_ARBITRATOR_MODEL", DEFAULT_ARBITRATOR_MODEL)
        self.high_intelligence_model = os.getenv(
            "HIFY_OPENROUTER_HIGH_INTELLIGENCE_MODEL",
            DEFAULT_HIGH_INTELLIGENCE_MODEL,
        )
        self.sop_model = os.getenv("OPENROUTER_MODEL", self.arbitrator_model)
        initialise_database()
        register_baseline_tables()
        _seed_default_live_agent(self.api_key, self.base_url, self.sop_model)

    def test_qwen_runs_representative_core_airline_three_sop_journeys(self) -> None:
        scenarios = _representative_live_scenarios()
        self.assertEqual(len(scenarios), 4)
        self.assertGreaterEqual(_average_words(scenarios), 5)
        self.assertFalse(any(_looks_like_direct_keyword(scenario.primary_utterance) for scenario in scenarios))

        classifier = _live_single_model_classifier(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.arbitrator_model,
            timeout=90.0,
            max_attempts=5,
            retry_sleep=2.0,
        )
        stamp = time.time_ns()
        results: list[dict[str, Any]] = []

        with TestClient(app) as client:
            bindings = _create_bindings(client, tuple(CORE_SOPS.values()), stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(bindings, classifier)
            try:
                for index, scenario in enumerate(scenarios):
                    results.append(_run_core_scenario(client, index, scenario))
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(len(results), 4)
        self.assertGreaterEqual(len(classifier.attempts), 4)
        self.assertTrue(all(result["completedSops"] == 3 for result in results))
        self.assertTrue(all(result["switchAction"] == "SUSPEND_AND_START" for result in results))
        self.assertTrue(all(result["resumeAction"] == "RESUME_TASK" for result in results))

        _write_artifact(
            base_url=self.base_url,
            arbitrator_model=self.arbitrator_model,
            high_intelligence_model=self.high_intelligence_model,
            sop_model=self.sop_model,
            classifier=classifier,
            results=results,
        )


def _runtime_service_override(
    bindings: dict[str, int],
    classifier: _SingleOpenRouterModelClassifier,
) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_service = WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            agent_repository=AgentRepository(session),
            model_facade=ProviderModelFacade(session),
            chatflow_state_repository=ChatflowStateRepository(session),
            llm_client_factory=_batch_live_llm_client,
        )
        adapter = ChatflowSopRuntimeAdapter(workflow_service, sop_chatflow_ids=bindings)
        return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter, classifier=classifier)

    return override


def _batch_live_llm_client(config: ProviderChatConfig) -> ProviderBackedOpenAIChatClient:
    return ProviderBackedOpenAIChatClient(config, timeout=90.0, max_attempts=5, retry_sleep=2.0)


def _create_bindings(client: TestClient, cases: tuple[LiveSopCase, ...], stamp: int) -> dict[str, int]:
    return {
        case.sop_id: int(cast(int | str, _create_live_chatflow_sop(client, case, stamp)["id"]))
        for case in cases
    }


def _core_scenarios() -> tuple[CoreScenario, ...]:
    scenarios: list[CoreScenario] = []
    for primary_index, primary_sop_id in enumerate(CORE_ORDER):
        secondary_sop_id = CORE_ORDER[(primary_index + 1) % len(CORE_ORDER)]
        tertiary_sop_id = CORE_ORDER[(primary_index + 2) % len(CORE_ORDER)]
        for utterance_index, primary_utterance in enumerate(CORE_START_UTTERANCES[primary_sop_id]):
            secondary_utterance = CORE_START_UTTERANCES[secondary_sop_id][utterance_index]
            tertiary_utterance = CORE_START_UTTERANCES[tertiary_sop_id][utterance_index]
            scenarios.append(
                CoreScenario(
                    business_area=primary_sop_id,
                    primary_sop_id=primary_sop_id,
                    primary_utterance=primary_utterance,
                    secondary_sop_id=secondary_sop_id,
                    secondary_utterance=secondary_utterance,
                    tertiary_sop_id=tertiary_sop_id,
                    tertiary_utterance=tertiary_utterance,
                )
            )
    return tuple(scenarios)


def _representative_live_scenarios() -> tuple[CoreScenario, ...]:
    scenarios = _core_scenarios()
    return (scenarios[0], scenarios[10], scenarios[20], scenarios[30])


def _run_single_sop_contract(client: TestClient, index: int, scenario: CoreScenario) -> dict[str, Any]:
    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
    started = _message(client, session_id, scenario.primary_utterance)
    details = _message(client, session_id, _details_for(index, scenario.primary_sop_id))
    completed = _message(client, session_id, "确认，按这个方案办理")

    assert started["routeDecision"]["action"] == "START_SOP"
    assert started["activeTask"]["sopId"] == scenario.primary_sop_id
    assert details["routeDecision"]["action"] == "CONTINUE_ACTIVE_SOP"
    assert completed["routeDecision"]["action"] == "COMPLETE_TASK"
    assert completed["activeTask"] is None
    return {
        "index": index,
        "primary": scenario.primary_sop_id,
        "startPolicyStage": (started["routeDecision"].get("policyGate") or {}).get("stage"),
        "completedSops": 1,
    }


def _run_core_scenario(client: TestClient, index: int, scenario: CoreScenario) -> dict[str, Any]:
    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

    primary_started = _message(client, session_id, scenario.primary_utterance)
    _assert_active(primary_started, "START_SOP", scenario.primary_sop_id, "info_order")

    secondary_started = _message(client, session_id, scenario.secondary_utterance)
    _assert_active(secondary_started, "SUSPEND_AND_START", scenario.secondary_sop_id, "info_order")
    _assert_live_arbitrator(secondary_started)

    _message(client, session_id, _details_for(index, scenario.secondary_sop_id))
    secondary_completed = _message(client, session_id, "确认，就按这个方案办理")
    _assert_live_sop_llm_reply(secondary_completed, CORE_SOPS[scenario.secondary_sop_id].marker)

    resumed = _message(client, session_id, CORE_SOPS[scenario.primary_sop_id].resume_message)
    _assert_active(resumed, "RESUME_TASK", scenario.primary_sop_id, "info_order")

    _message(client, session_id, _details_for(index, scenario.primary_sop_id))
    primary_completed = _message(client, session_id, "确认，继续完成刚才那单")
    _assert_live_sop_llm_reply(primary_completed, CORE_SOPS[scenario.primary_sop_id].marker)

    tertiary_started = _message(client, session_id, scenario.tertiary_utterance)
    _assert_active(tertiary_started, "START_SOP", scenario.tertiary_sop_id, "info_order")

    _message(client, session_id, _details_for(index, scenario.tertiary_sop_id))
    tertiary_completed = _message(client, session_id, "确认，按这个结果收尾")
    _assert_live_sop_llm_reply(tertiary_completed, CORE_SOPS[scenario.tertiary_sop_id].marker)

    return {
        "index": index,
        "primary": scenario.primary_sop_id,
        "secondary": scenario.secondary_sop_id,
        "tertiary": scenario.tertiary_sop_id,
        "primaryUtterance": scenario.primary_utterance,
        "switchAction": secondary_started["routeDecision"]["action"],
        "resumeAction": resumed["routeDecision"]["action"],
        "completedSops": 3,
    }


def _details_for(index: int, sop_id: str) -> str:
    phone = f"13920{index:06d}"
    if sop_id == "flight_booking":
        return (
            f"乘机人林测试，手机号 {phone}，下周二上午从北京出发到上海，"
            "差旅审批已经通过，出票后请短信通知"
        )
    return (
        f"订单号 MU{index:06d}，手机号 {phone}，乘机人林测试，"
        "明天上午从北京出发，备注希望短信通知"
    )


def _average_words(scenarios: Sequence[CoreScenario]) -> float:
    utterances = [scenario.primary_utterance for scenario in scenarios]
    return sum(len(item.strip()) for item in utterances) / len(utterances)


def _looks_like_direct_keyword(utterance: str) -> bool:
    direct = {"我要退票", "我要改签", "我要订票", "我要订机票", "我要咨询"}
    return utterance.strip() in direct


def _write_artifact(
    *,
    base_url: str,
    arbitrator_model: str,
    high_intelligence_model: str,
    sop_model: str,
    classifier: _SingleOpenRouterModelClassifier,
    results: Sequence[dict[str, Any]],
) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RuntimeLab Live Qwen Core Airline Scenarios",
        "",
        "- Slice: 034.12 live natural core airline gate",
        "- Scope: booking/refund/change/consultation, 10 natural scenarios each",
        "- Journey: A start -> B switch -> B complete -> resume A -> A complete -> C start -> C complete",
        f"- Base URL: `{base_url}`",
        f"- Arbitrator model: `{arbitrator_model}`",
        f"- High-intelligence optional model: `{high_intelligence_model}`",
        f"- Chatflow SOP LLM model: `{sop_model}`",
        f"- Scenario count: {len(results)}",
        f"- LLM arbitrator attempts: {len(classifier.attempts)}",
        "- API key: runtime environment only, not recorded",
        "",
        "## Results",
        "",
        "| # | A | B | C | Switch | Resume | Completed | Primary utterance |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for item in results:
        lines.append(
            "| {index} | `{primary}` | `{secondary}` | `{tertiary}` | `{switch}` | `{resume}` | {completed} | {utterance} |".format(
                index=item["index"],
                primary=item["primary"],
                secondary=item["secondary"],
                tertiary=item["tertiary"],
                switch=item["switchAction"],
                resume=item["resumeAction"],
                completed=item["completedSops"],
                utterance=item["primaryUtterance"],
            )
        )
    lines.append("")
    ARTIFACT_PATH.write_text("\n".join(lines), encoding="utf-8")
