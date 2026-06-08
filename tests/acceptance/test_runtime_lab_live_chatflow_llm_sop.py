from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import os
from pathlib import Path
import time
import unittest
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import Base, get_session, get_session_factory, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.agent.infra.repository import AgentRepository
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository

RUN_LIVE = os.getenv("HIFY_RUN_LIVE_RUNTIME_CHATFLOW") == "1"
ARTIFACT_PATH = Path("artifacts/slices/032-chatflow-sop-integration/032.5/live-chatflow-llm-acceptance.md")


@dataclass(frozen=True)
class LiveSopCase:
    sop_id: str
    display_name: str
    start_message: str
    resume_message: str
    phone: str

    @property
    def marker(self) -> str:
        return f"HIFY_{self.sop_id.upper()}_LIVE"


LIVE_SOPS = (
    LiveSopCase("refund_ticket", "退票", "我要退票", "继续处理退票", "13900000001"),
    LiveSopCase("change_flight", "改签", "我要改签", "继续处理改签", "13900000002"),
    LiveSopCase("invoice_apply", "发票申请", "我要开票", "继续处理发票", "13900000003"),
    LiveSopCase("baggage_service", "行李服务", "我要加行李", "继续处理行李服务", "13900000004"),
    LiveSopCase("seat_checkin", "值机选座", "我要选座", "继续处理值机选座", "13900000005"),
)


@unittest.skipUnless(
    RUN_LIVE,
    "Set HIFY_RUN_LIVE_RUNTIME_CHATFLOW=1 and OPENROUTER_API_KEY to run live RuntimeLab Chatflow LLM acceptance",
)
class RuntimeLabLiveChatflowLlmSopAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.model = os.getenv("OPENROUTER_MODEL", "xiaomi/mimo-v2-flash")
        initialise_database()
        register_baseline_tables()
        _seed_default_live_agent(self.api_key, self.base_url, self.model)

    def test_unified_router_executes_real_llm_nodes_inside_chatflow_sops(self) -> None:
        stamp = time.time_ns()
        comparisons: list[dict[str, Any]] = []
        with TestClient(app) as client:
            bindings = _create_live_chatflow_bindings(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(bindings)
            try:
                comparisons.extend(
                    _run_live_switch_journey(
                        client,
                        primary=_case("refund_ticket"),
                        secondary=_case("invoice_apply"),
                        scenario="live_refund_to_invoice_then_resume",
                    )
                )
                for sop_id in ("change_flight", "baggage_service", "seat_checkin"):
                    comparisons.append(_complete_live_sop(client, _case(sop_id), scenario=f"live_single_{sop_id}"))
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        for item in comparisons:
            actual_reply = str(item["actual"].get("reply") or "")
            self.assertIn(item["expected"]["marker"], actual_reply)
            self.assertNotIn("LLM mock:", actual_reply)
            self.assertNotIn("Workflow mock:", actual_reply)
            self.assertNotIn("RAG mock:", actual_reply)
        _write_artifact(self.base_url, self.model, comparisons)


def _run_live_switch_journey(
    client: TestClient,
    *,
    primary: LiveSopCase,
    secondary: LiveSopCase,
    scenario: str,
) -> list[dict[str, Any]]:
    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
    comparisons: list[dict[str, Any]] = []

    started = _message(client, session_id, primary.start_message)
    _assert_active(started, "START_SOP", primary.sop_id, "info_order")

    switched = _message(client, session_id, secondary.start_message)
    _assert_active(switched, "SUSPEND_AND_START", secondary.sop_id, "info_order")

    _message(client, session_id, f"手机号 {secondary.phone}")
    secondary_completed = _message(client, session_id, "确认")
    comparisons.append(
        _comparison(
            f"{scenario}:secondary_llm_complete",
            {"action": "COMPLETE_TASK", "marker": secondary.marker},
            secondary_completed,
        )
    )

    resumed = _message(client, session_id, primary.resume_message)
    _assert_active(resumed, "RESUME_TASK", primary.sop_id, "info_order")

    _message(client, session_id, f"手机号 {primary.phone}")
    primary_completed = _message(client, session_id, "确认")
    comparisons.append(
        _comparison(
            f"{scenario}:primary_llm_complete",
            {"action": "COMPLETE_TASK", "marker": primary.marker},
            primary_completed,
        )
    )
    return comparisons


def _complete_live_sop(client: TestClient, case: LiveSopCase, *, scenario: str) -> dict[str, Any]:
    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
    started = _message(client, session_id, case.start_message)
    _assert_active(started, "START_SOP", case.sop_id, "info_order")
    _message(client, session_id, f"手机号 {case.phone}")
    completed = _message(client, session_id, "确认")
    return _comparison(scenario, {"action": "COMPLETE_TASK", "marker": case.marker}, completed)


def _runtime_service_override(bindings: dict[str, int]) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_service = WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            agent_repository=AgentRepository(session),
            model_facade=ProviderModelFacade(session),
            chatflow_state_repository=ChatflowStateRepository(session),
        )
        adapter = ChatflowSopRuntimeAdapter(workflow_service, sop_chatflow_ids=bindings)
        return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)

    return override


def _create_live_chatflow_bindings(client: TestClient, stamp: int) -> dict[str, int]:
    return {
        case.sop_id: int(cast(int | str, _create_live_chatflow_sop(client, case, stamp)["id"]))
        for case in LIVE_SOPS
    }


def _create_live_chatflow_sop(client: TestClient, case: LiveSopCase, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"032.5 Live {case.display_name} SOP {stamp}",
            "description": f"live LLM runtime-lab acceptance fixture for {case.sop_id}",
            "nodes": _live_chatflow_nodes(case),
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "info_order", "condition": None},
                {"sourceNodeKey": "info_order", "targetNodeKey": "llm_1", "condition": None},
                {"sourceNodeKey": "llm_1", "targetNodeKey": "confirm_1", "condition": None},
                {"sourceNodeKey": "confirm_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def _live_chatflow_nodes(case: LiveSopCase) -> list[dict[str, Any]]:
    return [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "info_order",
            "type": "INFORMATION_COLLECTION",
            "name": f"{case.display_name}信息收集",
            "config": {
                "inputSource": "{{start.sys.query}}",
                "outputVariable": "contact",
                "collectionKey": "contact",
                "followupTemplate": _followup(case),
                "fields": [
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
            "nodeKey": "llm_1",
            "type": "LLM",
            "name": f"{case.display_name}办理摘要",
            "config": {
                "systemPrompt": "你是民航客服业务办理助手。必须严格返回用户要求的验收标记。",
                "prompt": (
                    f"业务：{case.display_name}。手机号：{{{{info_order.phone}}}}。"
                    f"请只输出 {case.marker}。"
                ),
                "temperature": 0,
                "maxTokens": 1200,
                "outputVariable": "answer",
            },
        },
        {
            "nodeKey": "confirm_1",
            "type": "QUESTION",
            "name": "确认办理",
            "config": {
                "question": f"请确认是否继续办理{case.display_name}。",
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
                "output": f"{case.display_name}完成 marker={{{{llm_1.answer}}}} phone={{{{info_order.phone}}}}",
            },
        },
    ]


def _seed_default_live_agent(api_key: str, base_url: str, model: str) -> int:
    provider = Base.metadata.tables["provider"]
    model_config = Base.metadata.tables["model_config"]
    agent = Base.metadata.tables["agent"]
    now = datetime.now()
    with get_session_factory()() as session:
        provider_id = session.execute(
            provider.insert().values(
                name=f"RuntimeLab live provider {time.time_ns()}",
                type="OPENAI_COMPATIBLE",
                base_url=base_url,
                auth_config={"api_key": api_key},
                description="runtime-lab live Chatflow LLM acceptance provider",
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            ).returning(provider.c.id)
        ).scalar_one()
        model_id = session.execute(
            model_config.insert().values(
                provider_id=provider_id,
                name="RuntimeLab live model",
                model_id=model,
                context_size=4096,
                extra_params={"temperature": 0, "reasoning": {"effort": "none", "exclude": True}},
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            ).returning(model_config.c.id)
        ).scalar_one()
        agent_id = session.execute(
            agent.insert().values(
                name=f"RuntimeLab live Chatflow agent {time.time_ns()}",
                description="runtime-lab live LLM SOP acceptance agent",
                system_prompt="",
                model_config_id=model_id,
                temperature=0,
                max_tokens=128,
                max_context_turns=6,
                enabled=True,
                deleted=False,
                created_at=now,
                updated_at=now,
            ).returning(agent.c.id)
        ).scalar_one()
        session.commit()
        return int(agent_id)


def _message(client: TestClient, session_id: int, message: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _assert_active(actual: dict[str, Any], action: str, sop_id: str, step: str) -> None:
    assert actual["routeDecision"]["action"] == action
    assert actual["activeTask"]["sopId"] == sop_id
    assert actual["activeTask"]["currentStep"] == step


def _followup(case: LiveSopCase) -> str:
    return f"请提供{case.display_name}办理手机号。"


def _case(sop_id: str) -> LiveSopCase:
    for item in LIVE_SOPS:
        if item.sop_id == sop_id:
            return item
    raise KeyError(sop_id)


def _comparison(label: str, expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    return {
        "label": label,
        "expected": expected,
        "actual": {
            "action": actual["routeDecision"]["action"],
            "reply": str(actual.get("reply") or "")[:240],
        },
    }


def _write_artifact(base_url: str, model: str, comparisons: list[dict[str, Any]]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RuntimeLab Live Chatflow LLM SOP Acceptance",
        "",
        "- Entry: `/api/v1/runtime-lab/sessions/{id}/messages`",
        "- Route control: runtime-lab unified router",
        "- Execution: real Chatflow SOPs through `ChatflowSopRuntimeAdapter`",
        "- LLM: live provider-backed Chatflow `LLM` nodes",
        f"- Base URL: `{base_url}`",
        f"- Model: `{model}`",
        "- API key: runtime environment only, not recorded",
        "",
        "| Case | Expected | Actual |",
        "| --- | --- | --- |",
    ]
    for item in comparisons:
        lines.append(f"| {item['label']} | `{item['expected']}` | `{item['actual']}` |")
    ARTIFACT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
