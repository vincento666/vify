import unittest

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service


class RuntimeLabApiE2ETest(unittest.TestCase):
    def test_switch_complete_resume_and_reject_non_interruptible_switch(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _fake_runtime_service
        try:
            with TestClient(app) as client:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                started = _message(client, session_id, "我要退票")
                switched = _message(client, session_id, "我要开发票")
                invoice_collected = _message(client, session_id, "INV-200")
                invoice_completed = _message(client, session_id, "确认")
                resumed = _message(client, session_id, "继续刚才")
                refund_collected = _message(client, session_id, "TK-100")
                rejected = _message(client, session_id, "我要改签")

                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
                events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(switched["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(invoice_collected["activeTask"]["currentStep"], "confirm")
        self.assertEqual(invoice_completed["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual(invoice_completed["resumeOffer"]["sopId"], "refund_ticket")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertEqual(refund_collected["activeTask"]["currentStep"], "confirm")
        self.assertEqual(rejected["routeDecision"]["action"], "REJECT_SWITCH_CONTINUE_ACTIVE")
        self.assertEqual([task["status"] for task in tasks], ["RUNNING", "COMPLETED"])
        self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))

    def test_explicit_handoff_preserves_active_task_and_emits_snapshot(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _fake_runtime_service
        try:
            with TestClient(app) as client:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                started = _message(client, session_id, "我要退票")
                handoff = _message(client, session_id, "我要人工客服")
                tasks = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/tasks").json()["data"]["list"]
                events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(handoff["routeDecision"]["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(handoff["routeDecision"]["handoff"]["reasonCode"], "USER_REQUEST")
        self.assertEqual(handoff["activeTask"]["id"], started["activeTask"]["id"])
        self.assertEqual(handoff["activeTask"]["currentStep"], started["activeTask"]["currentStep"])
        self.assertEqual([task["status"] for task in tasks], ["RUNNING"])
        requested = next(event for event in events if event["eventType"] == "HANDOFF_REQUESTED")
        self.assertEqual(requested["payload"]["contextSnapshot"]["activeTaskSummary"]["sopId"], "refund_ticket")
        self.assertEqual(requested["payload"]["contextSnapshot"]["routeEvidence"]["action"], "HANDOFF_TO_HUMAN")

    def test_exact_faq_answers_before_sop_and_preserves_active_sop_state(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _faq_runtime_service
        try:
            with TestClient(app) as client:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                faq = _message(client, session_id, "儿童票可以退吗？")
                started = _message(client, session_id, "我要退票")
                active_faq = _message(client, session_id, "儿童票可以退吗？")
                events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(faq["reply"], "儿童票如未使用可按客票规则申请退票。")
        self.assertEqual(faq["routeDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(faq["routeDecision"]["faqAnswer"]["sourceLayer"], "faq_exact")
        self.assertIsNone(faq["activeTask"])
        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(active_faq["routeDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(active_faq["activeTask"]["id"], started["activeTask"]["id"])
        self.assertEqual(active_faq["activeTask"]["currentStep"], started["activeTask"]["currentStep"])
        self.assertEqual(active_faq["activeTask"]["checkpointId"], started["activeTask"]["checkpointId"])
        self.assertIn("FAQ_ANSWERED", [event["eventType"] for event in events])


def _message(client: TestClient, session_id: int, message: str) -> dict:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200
    return response.json()["data"]


def _fake_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(RuntimeLabRepository(session))


def _faq_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(RuntimeLabRepository(session), faq_answer_gate=_StaticFaqGate())


class _StaticFaqGate:
    def propose(
        self,
        message: str,
        *,
        active_task: dict | None,
        suspended_tasks: list[dict],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        if "儿童票" not in message:
            return None
        return FaqAnswerProposal(
            answer="儿童票如未使用可按客票规则申请退票。",
            confidence=1.0,
            margin=1.0,
            evidence=FaqAnswerEvidence(
                faq_id=12,
                question="儿童票可以退吗？",
                answer="儿童票如未使用可按客票规则申请退票。",
                score=2.0,
                match_type="EXACT",
                source="structured_faq",
                matched_terms=("儿童票可以退吗",),
            ),
        )
