from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
import time
import unittest
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository

ARTIFACT_PATH = Path("artifacts/slices/032-chatflow-sop-integration/032.5/airline-business-gate.md")


@dataclass(frozen=True)
class SopCase:
    sop_id: str
    display_name: str
    start_message: str
    resume_message: str
    phone: str


AIRLINE_SOPS = (
    SopCase("refund_ticket", "退票", "我要退票", "继续处理退票", "13800000001"),
    SopCase("change_flight", "改签", "我要改签", "继续处理改签", "13800000002"),
    SopCase("invoice_apply", "发票申请", "我要开票", "继续处理发票", "13800000003"),
    SopCase("baggage_service", "行李服务", "我要加行李", "继续处理行李服务", "13800000004"),
    SopCase("seat_checkin", "值机选座", "我要选座", "继续处理值机选座", "13800000005"),
)


class RuntimeLabAirlineSopBusinessGateTest(unittest.TestCase):
    def test_all_five_airline_sops_start_through_unified_router_into_real_chatflows(self) -> None:
        stamp = time.time_ns()
        comparisons: list[dict[str, Any]] = []
        with TestClient(app) as client:
            bindings = _create_chatflow_bindings(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(bindings)
            try:
                for case in AIRLINE_SOPS:
                    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
                    actual = _message(client, session_id, case.start_message)
                    expected = {"action": "START_SOP", "sopId": case.sop_id, "step": "info_order"}
                    comparisons.append(_comparison(f"start:{case.sop_id}", expected, actual))
                    self.assertEqual(actual["routeDecision"]["action"], expected["action"])
                    self.assertEqual(actual["activeTask"]["sopId"], expected["sopId"])
                    self.assertEqual(actual["activeTask"]["currentStep"], expected["step"])
                    self.assertIn("phone", actual["reply"])
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)
        _write_artifact("Five SOP start coverage", comparisons)

    def test_three_high_probability_cross_sop_journeys_match_expected_route_outputs(self) -> None:
        stamp = time.time_ns()
        comparisons: list[dict[str, Any]] = []
        with TestClient(app) as client:
            bindings = _create_chatflow_bindings(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(bindings)
            try:
                comparisons.extend(
                    _run_switch_complete_resume_journey(
                        client,
                        primary=_case("refund_ticket"),
                        secondary=_case("invoice_apply"),
                        scenario="refund_to_invoice_then_resume",
                    )
                )
                comparisons.extend(
                    _run_switch_complete_resume_journey(
                        client,
                        primary=_case("change_flight"),
                        secondary=_case("baggage_service"),
                        scenario="change_to_baggage_then_resume",
                        rejected_switch=_case("seat_checkin"),
                    )
                )
                comparisons.extend(
                    _run_switch_complete_resume_journey(
                        client,
                        primary=_case("seat_checkin"),
                        secondary=_case("refund_ticket"),
                        scenario="seat_to_refund_then_resume",
                    )
                )
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)
        _write_artifact("Cross-SOP journey coverage", comparisons)


def _run_switch_complete_resume_journey(
    client: TestClient,
    *,
    primary: SopCase,
    secondary: SopCase,
    scenario: str,
    rejected_switch: SopCase | None = None,
) -> list[dict[str, Any]]:
    session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
    comparisons: list[dict[str, Any]] = []

    started = _message(client, session_id, primary.start_message)
    comparisons.append(_comparison(f"{scenario}:start_primary", {"action": "START_SOP", "sopId": primary.sop_id}, started))
    _assert_turn(started, "START_SOP", primary.sop_id, "info_order")

    switched = _message(client, session_id, secondary.start_message)
    comparisons.append(
        _comparison(f"{scenario}:switch_secondary", {"action": "SUSPEND_AND_START", "sopId": secondary.sop_id}, switched)
    )
    _assert_turn(switched, "SUSPEND_AND_START", secondary.sop_id, "info_order")
    self_check = switched["suspendedTasks"][0]
    assert self_check["sopId"] == primary.sop_id

    secondary_collected = _message(client, session_id, f"手机号 {secondary.phone}")
    comparisons.append(
        _comparison(
            f"{scenario}:secondary_collect",
            {"action": "CONTINUE_ACTIVE_SOP", "sopId": secondary.sop_id, "step": "confirm_1"},
            secondary_collected,
        )
    )
    _assert_turn(secondary_collected, "CONTINUE_ACTIVE_SOP", secondary.sop_id, "confirm_1")

    secondary_completed = _message(client, session_id, "确认")
    comparisons.append(
        _comparison(f"{scenario}:secondary_complete", {"action": "COMPLETE_TASK", "resumeSopId": primary.sop_id}, secondary_completed)
    )
    assert secondary_completed["routeDecision"]["action"] == "COMPLETE_TASK"
    assert secondary_completed["resumeOffer"]["sopId"] == primary.sop_id

    resumed = _message(client, session_id, primary.resume_message)
    comparisons.append(_comparison(f"{scenario}:resume_primary", {"action": "RESUME_TASK", "sopId": primary.sop_id}, resumed))
    _assert_turn(resumed, "RESUME_TASK", primary.sop_id, "info_order")

    primary_collected = _message(client, session_id, f"手机号 {primary.phone}")
    comparisons.append(
        _comparison(
            f"{scenario}:primary_collect",
            {"action": "CONTINUE_ACTIVE_SOP", "sopId": primary.sop_id, "step": "confirm_1"},
            primary_collected,
        )
    )
    _assert_turn(primary_collected, "CONTINUE_ACTIVE_SOP", primary.sop_id, "confirm_1")

    if rejected_switch is not None:
        rejected = _message(client, session_id, rejected_switch.start_message)
        comparisons.append(
            _comparison(
                f"{scenario}:reject_non_interruptible_switch",
                {"action": "REJECT_SWITCH_CONTINUE_ACTIVE", "sopId": primary.sop_id},
                rejected,
            )
        )
        _assert_turn(rejected, "REJECT_SWITCH_CONTINUE_ACTIVE", primary.sop_id, "confirm_1")

    primary_completed = _message(client, session_id, "确认")
    comparisons.append(_comparison(f"{scenario}:primary_complete", {"action": "COMPLETE_TASK"}, primary_completed))
    assert primary_completed["routeDecision"]["action"] == "COMPLETE_TASK"
    assert primary_completed["activeTask"] is None
    return comparisons


def _runtime_service_override(bindings: dict[str, int]) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_service = WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            chatflow_state_repository=ChatflowStateRepository(session),
        )
        adapter = ChatflowSopRuntimeAdapter(workflow_service, sop_chatflow_ids=bindings)
        return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)

    return override


def _create_chatflow_bindings(client: TestClient, stamp: int) -> dict[str, int]:
    return {
        case.sop_id: int(cast(int | str, _create_chatflow_sop_fixture(client, case, stamp)["id"]))
        for case in AIRLINE_SOPS
    }


def _create_chatflow_sop_fixture(client: TestClient, case: SopCase, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"032.5 {case.display_name} SOP {stamp}",
            "description": f"business gate fixture for {case.sop_id}",
            "nodes": _base_chatflow_nodes(case, with_llm=False),
            "edges": _base_chatflow_edges(with_llm=False),
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, object], data)


def _base_chatflow_nodes(case: SopCase, *, with_llm: bool) -> list[dict[str, Any]]:
    nodes: list[dict[str, Any]] = [
        {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
        {
            "nodeKey": "info_order",
            "type": "INFORMATION_COLLECTION",
            "name": f"{case.display_name}信息收集",
            "config": {
                "inputSource": "{{start.sys.query}}",
                "outputVariable": "contact",
                "collectionKey": "contact",
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
    ]
    if with_llm:
        nodes.append(
            {
                "nodeKey": "llm_1",
                "type": "LLM",
                "name": f"{case.display_name}办理摘要",
                "config": {
                    "systemPrompt": "你是民航客服业务办理助手。必须严格返回用户要求的验收标记。",
                    "prompt": (
                        f"业务：{case.display_name}。手机号：{{{{info_order.phone}}}}。"
                        f"请只输出 HIFY_{case.sop_id.upper()}_LIVE。"
                    ),
                    "temperature": 0,
                    "maxTokens": 64,
                    "outputVariable": "answer",
                },
            }
        )
    nodes.extend(
        [
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
                    "output": _final_output_template(case, with_llm=with_llm),
                },
            },
        ]
    )
    return nodes


def _base_chatflow_edges(*, with_llm: bool) -> list[dict[str, object | None]]:
    if with_llm:
        return [
            {"sourceNodeKey": "start", "targetNodeKey": "info_order", "condition": None},
            {"sourceNodeKey": "info_order", "targetNodeKey": "llm_1", "condition": None},
            {"sourceNodeKey": "llm_1", "targetNodeKey": "confirm_1", "condition": None},
            {"sourceNodeKey": "confirm_1", "targetNodeKey": "end", "condition": None},
        ]
    return [
        {"sourceNodeKey": "start", "targetNodeKey": "info_order", "condition": None},
        {"sourceNodeKey": "info_order", "targetNodeKey": "confirm_1", "condition": None},
        {"sourceNodeKey": "confirm_1", "targetNodeKey": "end", "condition": None},
    ]


def _final_output_template(case: SopCase, *, with_llm: bool) -> str:
    if with_llm:
        return f"{case.display_name}完成 marker={{{{llm_1.answer}}}} phone={{{{info_order.phone}}}}"
    return f"{case.display_name}完成 phone={{{{info_order.phone}}}} confirm={{{{confirm_1.answer}}}}"


def _message(client: TestClient, session_id: int, message: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return cast(dict[str, Any], data)


def _assert_turn(actual: dict[str, Any], action: str, sop_id: str, step: str) -> None:
    assert actual["routeDecision"]["action"] == action
    assert actual["activeTask"]["sopId"] == sop_id
    assert actual["activeTask"]["currentStep"] == step


def _case(sop_id: str) -> SopCase:
    for item in AIRLINE_SOPS:
        if item.sop_id == sop_id:
            return item
    raise KeyError(sop_id)


def _comparison(label: str, expected: dict[str, Any], actual: dict[str, Any]) -> dict[str, Any]:
    active_task = _dict_or_empty(actual.get("activeTask"))
    resume_offer = _dict_or_empty(actual.get("resumeOffer"))
    return {
        "label": label,
        "expected": expected,
        "actual": {
            "action": actual["routeDecision"]["action"],
            "sopId": active_task.get("sopId"),
            "step": active_task.get("currentStep"),
            "resumeSopId": resume_offer.get("sopId"),
            "reply": str(actual.get("reply") or "")[:120],
        },
    }


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return cast(dict[str, Any], value) if isinstance(value, dict) else {}


def _write_artifact(title: str, comparisons: list[dict[str, Any]]) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", "", "| Case | Expected | Actual |", "| --- | --- | --- |"]
    for item in comparisons:
        lines.append(
            "| {label} | `{expected}` | `{actual}` |".format(
                label=item["label"],
                expected=item["expected"],
                actual=item["actual"],
            )
        )
    ARTIFACT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
