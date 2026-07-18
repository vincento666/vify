from collections.abc import Callable
import time
import unittest
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session, get_session_factory
from app.main import app
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service
from app.modules.runtime_lab.web.router import _runtime_lab_background_enqueue, _runtime_lab_background_resume_enqueue
from app.modules.workflow.domain.runtime_invocation_gateway import RuntimeInvocationGateway
from app.modules.workflow.domain.runtime_v2 import ChatflowRuntimeV2Service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.runtime_job_worker import build_runtime_job_worker


class RuntimeLabChatflowSopApiE2ETest(unittest.TestCase):
    def test_runtime_api_rejects_switch_without_a_durable_legacy_checkpoint(self) -> None:
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
                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
                events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(started["activeTask"]["sopId"], "refund_ticket")
        self.assertNotIn("currentStep", started["activeTask"])
        self.assertIn("phone", started["reply"])
        self.assertEqual(switched["routeDecision"]["action"], "REJECT_SWITCH_CONTINUE_ACTIVE")
        self.assertEqual(switched["activeTask"]["sopId"], "refund_ticket")
        self.assertNotIn("currentStep", switched["activeTask"])
        self.assertEqual([task["sopId"] for task in tasks], ["refund_ticket"])
        self.assertEqual([task["status"] for task in tasks], ["RUNNING"])
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))

    def test_runtime_api_switches_to_runtime_v2_chatflow_with_durable_checkpoint(self) -> None:
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
                _drain_chatflow_runtime_job(started, stamp)
                switched = _message(client, session_id, "我要开发票")
                _drain_chatflow_runtime_job(switched, stamp)
                invoice_collected = _message(client, session_id, "手机号 13900139000")
                _drain_chatflow_runtime_job(invoice_collected, stamp)
                invoice_completed = _message(client, session_id, "确认")
                _drain_chatflow_runtime_job(invoice_completed, stamp)
                invoice_finished = _message(client, session_id, "确认")
                resumed = _message(client, session_id, "继续处理退票")
                self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK", resumed)
                _drain_chatflow_runtime_job(resumed, stamp)
                refund_collected = _message(client, session_id, "手机号 13800138000")
                _drain_chatflow_runtime_job(refund_collected, stamp)
                refund_completed = _message(client, session_id, "确认")
                _drain_chatflow_runtime_job(refund_completed, stamp)
                refund_finished = _message(client, session_id, "确认")

                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
                trace = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/chatflow-trace").json()["data"]
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertNotIn("currentStep", started["activeTask"])
        self.assertEqual(switched["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(switched["activeTask"]["sopId"], "invoice_apply")
        self.assertNotIn("currentStep", switched["activeTask"])
        self.assertEqual(invoice_finished["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual(invoice_finished["resumeOffer"]["sopId"], "refund_ticket")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertEqual(refund_finished["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual([task["sopId"] for task in tasks], ["refund_ticket", "invoice_apply"])
        self.assertEqual([task["status"] for task in tasks], ["COMPLETED", "COMPLETED"])

        refund_trace = next(task for task in trace["tasks"] if task["sopId"] == "refund_ticket")
        refund_run_id = refund_trace["chatflow"]["runId"]
        self.assertEqual(refund_trace["chatflow"]["statusRef"], f"/api/v1/runtime-runs/{refund_run_id}")
        self.assertEqual(refund_trace["chatflow"]["eventsRef"], f"/api/v1/runtime-runs/{refund_run_id}/events")
        self.assertEqual(
            refund_trace["chatflow"]["eventStreamRef"],
            f"/api/v1/runtime-runs/{refund_run_id}/events/stream?afterSequence=0",
        )
        self.assertEqual(refund_trace["chatflow"]["nodesRef"], f"/api/v1/runtime-runs/{refund_run_id}/nodes")
        self.assertEqual(refund_trace["chatflow"]["resultRef"], f"/api/v1/runtime-runs/{refund_run_id}/result")
        event_types = [event["type"] for event in refund_trace["events"]]
        self.assertIn("workflow_run_started", event_types)
        self.assertIn("workflow_node_waiting", event_types)

        with TestClient(app) as client:
            raw_events_response = client.get(refund_trace["chatflow"]["eventsRef"])
        self.assertEqual(raw_events_response.status_code, 200, raw_events_response.text)
        raw_events = raw_events_response.json()["data"]["list"]
        contextual_events = [
            event
            for event in raw_events
            if event["type"] in {"workflow_run_started", "workflow_node_waiting"}
        ]
        self.assertTrue(contextual_events)
        for event in contextual_events:
            context = event["payload"]["callerContext"]
            self.assertEqual(context["source"], "runtime-lab")
            self.assertEqual(context["sop_key"], "refund_ticket")
            self.assertEqual(context["session_id"], str(session_id))
            self.assertEqual(context["task_id"], str(refund_trace["taskId"]))


def _runtime_service_override(chatflow_id: int, *, runtime_v2: bool = False) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_repository = WorkflowRepository(session)
        state_repository = ChatflowStateRepository(session)
        workflow_service = WorkflowService(
            workflow_repository,
            flow_type="CHATFLOW",
            chatflow_state_repository=state_repository,
        )
        runtime_v2_service = (
            ChatflowRuntimeV2Service(
                workflow_repository,
                state_repository,
                completion_delay_seconds=0,
            )
            if runtime_v2
            else None
        )
        runtime_v2_gateway = (
            RuntimeInvocationGateway(
                runtime_v2_service,
                enqueue_background_run=_runtime_lab_background_enqueue(session, sop_llm_mode="mock"),
                enqueue_background_resume=_runtime_lab_background_resume_enqueue(session, sop_llm_mode="mock"),
            )
            if runtime_v2_service is not None
            else None
        )
        adapter = ChatflowSopRuntimeAdapter(
            workflow_service,
            sop_chatflow_ids={"refund_ticket": chatflow_id, "invoice_apply": chatflow_id},
            fallback_adapter=FakeSopRuntimeAdapter(),
            runtime_v2_service=runtime_v2_service,
            runtime_invocation_gateway=runtime_v2_gateway,
            runtime_invocation_mode="async",
        )
        return RuntimeLabService(
            RuntimeLabRepository(session),
            adapter=adapter,
            current_step_runtime=runtime_v2_service,
        )

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


def _drain_chatflow_runtime_job(turn: dict[str, Any], stamp: int) -> None:
    active_task = cast(dict[str, Any], turn["activeTask"])
    chatflow_session = cast(dict[str, Any], active_task["chatflowSession"])
    run_id = int(chatflow_session["runId"])
    with get_session_factory()() as session:
        jobs = [
            job
            for job in RuntimeJobRepository(session).list_active_for_queue_gate()
            if int(job["run_id"]) == run_id
        ]
        assert len(jobs) == 1, jobs
        result = build_runtime_job_worker(
            session,
            owner="chatflow",
            worker_id=f"runtime-lab-e2e-{stamp}-{run_id}",
        ).run_once(job_id=int(jobs[0]["id"]))
    assert result["status"] == "COMPLETED", result


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
