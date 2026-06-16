from collections.abc import Callable
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
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository


class RuntimeLabChatflowSopApiE2ETest(unittest.TestCase):
    def test_runtime_api_switches_away_and_resumes_real_chatflow_sop(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(
                int(cast(int | str, chatflow["id"]))
            )
            try:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                started = _message(client, session_id, "我要退票")
                switched = _message(client, session_id, "我要开发票")
                invoice_collected = _message(client, session_id, "INV-200")
                invoice_completed = _message(client, session_id, "确认")
                resumed = _message(client, session_id, "继续处理退票")
                refund_collected = _message(client, session_id, "手机号 13800138000")
                refund_completed = _message(client, session_id, "确认")

                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
                events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(started["activeTask"]["sopId"], "refund_ticket")
        self.assertEqual(started["activeTask"]["currentStep"], "info_order")
        self.assertIn("phone", started["reply"])
        self.assertEqual(switched["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(switched["activeTask"]["sopId"], "invoice_apply")
        self.assertEqual(invoice_collected["activeTask"]["currentStep"], "confirm")
        self.assertEqual(invoice_completed["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual(invoice_completed["resumeOffer"]["sopId"], "refund_ticket")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertEqual(resumed["activeTask"]["sopId"], "refund_ticket")
        self.assertEqual(resumed["activeTask"]["currentStep"], "info_order")
        self.assertEqual(refund_collected["activeTask"]["currentStep"], "confirm_1")
        self.assertEqual(refund_collected["activeTask"]["businessRefs"]["phone"], "13800138000")
        self.assertEqual(refund_completed["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual(refund_completed["activeTask"], None)
        self.assertEqual([task["sopId"] for task in tasks], ["refund_ticket", "invoice_apply"])
        self.assertEqual([task["status"] for task in tasks], ["COMPLETED", "COMPLETED"])
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))

    def test_runtime_api_switches_away_and_resumes_runtime_v2_chatflow_sop(self) -> None:
        stamp = time.time_ns()
        with TestClient(app) as client:
            chatflow = _create_chatflow_sop_fixture(client, stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(
                int(cast(int | str, chatflow["id"])),
                runtime_v2=True,
            )
            try:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                started = _message(client, session_id, "我要退票")
                switched = _message(client, session_id, "我要开发票")
                invoice_collected = _message(client, session_id, "INV-200")
                invoice_completed = _message(client, session_id, "确认")
                resumed = _message(client, session_id, "继续处理退票")
                refund_collected = _message(client, session_id, "手机号 13800138000")
                refund_completed = _message(client, session_id, "确认")

                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
                trace = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/chatflow-trace").json()["data"]
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(started["activeTask"]["currentStep"], "info_order")
        self.assertEqual(switched["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(invoice_collected["activeTask"]["currentStep"], "confirm")
        self.assertEqual(invoice_completed["resumeOffer"]["sopId"], "refund_ticket")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertNotIn("SOP执行失败", resumed["reply"])
        self.assertEqual(resumed["activeTask"]["currentStep"], "info_order")
        self.assertEqual(refund_collected["activeTask"]["currentStep"], "confirm_1")
        self.assertEqual(refund_collected["activeTask"]["businessRefs"]["phone"], "13800138000")
        self.assertEqual(refund_completed["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual([task["sopId"] for task in tasks], ["refund_ticket", "invoice_apply"])
        self.assertEqual([task["status"] for task in tasks], ["COMPLETED", "COMPLETED"])

        refund_trace = next(task for task in trace["tasks"] if task["sopId"] == "refund_ticket")
        event_types = [event["type"] for event in refund_trace["events"]]
        self.assertIn("workflow_run_started", event_types)
        self.assertIn("workflow_run_resumed", event_types)
        self.assertIn("workflow_node_waiting", event_types)


def _runtime_service_override(chatflow_id: int, *, runtime_v2: bool = False) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_repository = WorkflowRepository(session)
        state_repository = ChatflowStateRepository(session)
        workflow_service = WorkflowService(
            workflow_repository,
            flow_type="CHATFLOW",
            chatflow_state_repository=state_repository,
        )
        adapter = ChatflowSopRuntimeAdapter(
            workflow_service,
            sop_chatflow_ids={"refund_ticket": chatflow_id},
            fallback_adapter=FakeSopRuntimeAdapter(),
            runtime_v2_service=ChatflowRuntimeV2Service(
                workflow_repository,
                state_repository,
                completion_delay_seconds=0,
            )
            if runtime_v2
            else None,
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


def _create_chatflow_sop_fixture(client: TestClient, stamp: int) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"032 Runtime API SOP {stamp}",
            "description": "test-only runtime API Chatflow SOP fixture",
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
                        "output": "phone={{info_order.phone}} confirm={{confirm_1.answer}}",
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
