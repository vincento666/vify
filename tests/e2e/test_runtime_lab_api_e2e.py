import unittest

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal, FaqSemanticAnswerGate
from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagAnswerGate
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

    def test_semantic_faq_answers_and_low_margin_clarifies(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _semantic_faq_runtime_service
        try:
            with TestClient(app) as client:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                semantic = _message(client, session_id, "儿童机票能不能返钱？")
                low_margin = _message(client, session_id, "儿童机票规则怎么算？")
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(semantic["routeDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(semantic["routeDecision"]["faqAnswer"]["sourceLayer"], "faq_semantic")
        self.assertTrue(semantic["routeDecision"]["faqAnswer"]["evidence"]["rerankUsed"])
        self.assertEqual(low_margin["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(low_margin["routeDecision"]["faqAnswer"]["reasonCode"], "SEMANTIC_LOW_MARGIN")

    def test_rag_answers_no_active_and_preserves_active_sop_state(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _rag_runtime_service
        try:
            with TestClient(app) as client:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                rag = _message(client, session_id, "航班延误超过 4 小时保险怎么赔？")
                started = _message(client, session_id, "我要退票")
                active_rag = _message(client, session_id, "航班延误保险怎么赔？")
                events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(rag["routeDecision"]["action"], "ANSWER_RAG")
        self.assertEqual(rag["routeDecision"]["ragAnswer"]["sourceLayer"], "rag_policy")
        self.assertEqual(rag["routeDecision"]["ragAnswer"]["citations"][0]["sourceId"], "chunk:70")
        self.assertIsNone(rag["activeTask"])
        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(active_rag["routeDecision"]["action"], "ANSWER_RAG")
        self.assertEqual(active_rag["activeTask"]["id"], started["activeTask"]["id"])
        self.assertEqual(active_rag["activeTask"]["currentStep"], started["activeTask"]["currentStep"])
        self.assertEqual(active_rag["activeTask"]["checkpointId"], started["activeTask"]["checkpointId"])
        self.assertIn("RAG_ANSWERED", [event["eventType"] for event in events])

    def test_unresolved_query_reaches_controlled_agent_fallback_api(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            fallback = _message(client, session_id, "机场大巴末班车几点")
            events = client.get(f"/api/v1/runtime-lab/sessions/{session_id}/events").json()["data"]["list"]

        self.assertEqual(fallback["routeDecision"]["action"], "AGENT_FALLBACK")
        self.assertEqual(fallback["routeDecision"]["finalDecision"]["sourceLayer"], "agent_policy")
        self.assertEqual(fallback["routeDecision"]["agentAnswer"]["reasonCode"], "AGENT_ANSWER")
        self.assertFalse(fallback["routeDecision"]["agentAnswer"]["mutatesSopState"])
        self.assertIsNone(fallback["activeTask"])
        self.assertIn("AGENT_FALLBACK_ANSWERED", [event["eventType"] for event in events])


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


def _semantic_faq_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(
        RuntimeLabRepository(session),
        faq_semantic_gate=FaqSemanticAnswerGate(_SemanticFaqFacade(), knowledge_base_ids=[33], rerank=True),
    )


def _rag_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(
        RuntimeLabRepository(session),
        rag_answer_gate=RagAnswerGate(
            _RagFacade(),
            knowledge_base_ids=[33],
            generator=FakeRagAnswerGenerator(),
            rerank=True,
        ),
    )


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


class _SemanticFaqFacade:
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list["_SemanticFaqHit"]:
        del knowledge_base_id, top_k, retrieval_mode, score_threshold, rerank
        if query == "儿童机票能不能返钱？":
            return [
                _SemanticFaqHit(37, "儿童票退票规则", "儿童票如未使用可按客票规则申请退票。", 0.93),
                _SemanticFaqHit(38, "婴儿票退票规则", "婴儿票退票以客票规则为准。", 0.70),
            ]
        if query == "儿童机票规则怎么算？":
            return [
                _SemanticFaqHit(37, "儿童票退票规则", "儿童票如未使用可按客票规则申请退票。", 0.88),
                _SemanticFaqHit(39, "儿童票改签规则", "儿童票改签按客票规则办理。", 0.84),
            ]
        return []


class _SemanticFaqHit:
    source_type = "FAQ"
    match_type = "VECTOR"

    def __init__(self, faq_id: int, title: str, answer: str, score: float) -> None:
        self.faq_id = faq_id
        self.title = title
        self.answer = answer
        self.score = score


class _RagFacade:
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list["_RagHit"]:
        del knowledge_base_id, top_k, retrieval_mode, score_threshold, rerank
        if query in {"航班延误超过 4 小时保险怎么赔？", "航班延误保险怎么赔？"}:
            return [
                _RagHit(
                    chunk_id=70,
                    title="航班延误险条款",
                    content="航班延误超过 4 小时，可提交保险理赔申请。",
                    score=0.91,
                )
            ]
        return []


class _RagHit:
    source_type = "DOCUMENT_CHUNK"
    match_type = "VECTOR"
    document_id = 7
    chunk_index = 0

    def __init__(self, chunk_id: int, title: str, content: str, score: float) -> None:
        self.chunk_id = chunk_id
        self.title = title
        self.content = content
        self.score = score
