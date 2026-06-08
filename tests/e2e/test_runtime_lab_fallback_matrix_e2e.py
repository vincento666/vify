import unittest
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.agent_fallback import AgentOutputPolicy, FallbackAgentOutput, FallbackAgentRequest
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal
from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagAnswerGate
from app.modules.runtime_lab.domain.router import RouteDecision
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service


class RuntimeLabFallbackMatrixE2ETest(unittest.TestCase):
    def test_full_runtime_fallback_matrix(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _matrix_runtime_service
        try:
            with TestClient(app) as client:
                explicit_no_active = _new_session(client)
                explicit_handoff = _message(client, explicit_no_active, "我要人工客服")

                active_handoff_session = _new_session(client)
                active_started = _message(client, active_handoff_session, "我要退票")
                active_handoff = _message(client, active_handoff_session, "我要人工客服")

                exact_session = _new_session(client)
                exact_faq = _message(client, exact_session, "儿童票可以退吗")

                active_faq_session = _new_session(client)
                active_faq_started = _message(client, active_faq_session, "我要退票")
                active_faq = _message(client, active_faq_session, "儿童票可以退吗")

                semantic_session = _new_session(client)
                semantic_faq = _message(client, semantic_session, "小朋友的票能不能退回来")

                rag_session = _new_session(client)
                rag = _message(client, rag_session, "航班延误超过4小时保险怎么赔？")

                ambiguous_session = _new_session(client)
                ambiguous_started = _message(client, ambiguous_session, "我要退票")
                ambiguous = _message(client, ambiguous_session, "外星权益")

                escalation_session = _new_session(client)
                escalation_started = _message(client, escalation_session, "我要退票")
                clarify_one = _message(client, escalation_session, "不知道")
                clarify_two = _message(client, escalation_session, "还是那个")
                escalated = _message(client, escalation_session, "不知道")

                agent_session = _new_session(client)
                agent_answer = _message(client, agent_session, "机场大巴末班车几点")

                agent_handoff_session = _new_session(client)
                agent_handoff = _message(client, agent_handoff_session, "航司系统赔付争议材料很多需要进一步判断")

                sop_session = _new_session(client)
                refund_started = _message(client, sop_session, "我要退票")
                invoice_started = _message(client, sop_session, "我要开发票")
                _message(client, sop_session, "INV-200")
                invoice_completed = _message(client, sop_session, "确认")
                resumed = _message(client, sop_session, "继续退票")

                non_interrupt_session = _new_session(client)
                _message(client, non_interrupt_session, "我要退票")
                _message(client, non_interrupt_session, "TK-100")
                rejected_switch = _message(client, non_interrupt_session, "我要改签")
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(explicit_handoff["routeDecision"]["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(explicit_handoff["routeDecision"]["finalDecision"]["sourceLayer"], "explicit_signal")

        self.assertEqual(active_handoff["routeDecision"]["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(active_handoff["activeTask"]["id"], active_started["activeTask"]["id"])
        self.assertEqual(active_handoff["activeTask"]["checkpointId"], active_started["activeTask"]["checkpointId"])

        self.assertEqual(exact_faq["routeDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(exact_faq["routeDecision"]["finalDecision"]["sourceLayer"], "faq_exact")
        self.assertIsNone(exact_faq["routeDecision"]["classifierRequest"])

        self.assertEqual(active_faq["routeDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(active_faq["activeTask"]["id"], active_faq_started["activeTask"]["id"])
        self.assertEqual(active_faq["activeTask"]["checkpointId"], active_faq_started["activeTask"]["checkpointId"])
        self.assertFalse(active_faq["routeDecision"]["faqAnswer"]["mutatesSopState"])

        self.assertEqual(semantic_faq["routeDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(semantic_faq["routeDecision"]["finalDecision"]["sourceLayer"], "faq_semantic")
        self.assertTrue(semantic_faq["routeDecision"]["faqAnswer"]["evidence"]["rerankUsed"])

        self.assertEqual(rag["routeDecision"]["action"], "ANSWER_RAG")
        self.assertEqual(rag["routeDecision"]["finalDecision"]["sourceLayer"], "rag_policy")
        self.assertEqual(rag["routeDecision"]["ragAnswer"]["citations"][0]["sourceId"], "chunk:70")
        self.assertIsNone(rag["routeDecision"]["classifierRequest"])

        self.assertEqual(ambiguous["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(ambiguous["routeDecision"]["finalDecision"]["sourceLayer"], "agent_policy")
        self.assertEqual(ambiguous["activeTask"]["id"], ambiguous_started["activeTask"]["id"])

        self.assertEqual(clarify_one["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(clarify_two["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(escalated["routeDecision"]["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(escalated["routeDecision"]["handoff"]["reasonCode"], "CLARIFICATION_FAILED")
        self.assertEqual(escalated["activeTask"]["id"], escalation_started["activeTask"]["id"])

        self.assertEqual(agent_answer["routeDecision"]["action"], "AGENT_FALLBACK")
        self.assertEqual(agent_answer["routeDecision"]["finalDecision"]["sourceLayer"], "agent_policy")
        self.assertFalse(agent_answer["routeDecision"]["agentAnswer"]["mutatesSopState"])

        self.assertEqual(agent_handoff["routeDecision"]["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(agent_handoff["routeDecision"]["handoff"]["reasonCode"], "AGENT_RECOMMENDED_HANDOFF")

        self.assertEqual(refund_started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(refund_started["routeDecision"]["finalDecision"]["sourceLayer"], "sop_arbitration")
        self.assertEqual(invoice_started["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(invoice_started["routeDecision"]["finalDecision"]["sourceLayer"], "sop_arbitration")
        self.assertEqual(invoice_completed["routeDecision"]["action"], "COMPLETE_TASK")
        self.assertEqual(invoice_completed["routeDecision"]["finalDecision"]["sourceLayer"], "sop_arbitration")
        self.assertEqual(resumed["routeDecision"]["action"], "RESUME_TASK")
        self.assertEqual(resumed["routeDecision"]["finalDecision"]["sourceLayer"], "sop_arbitration")
        self.assertEqual(resumed["activeTask"]["sopId"], "refund_ticket")

        self.assertEqual(rejected_switch["routeDecision"]["action"], "REJECT_SWITCH_CONTINUE_ACTIVE")
        self.assertEqual(rejected_switch["routeDecision"]["finalDecision"]["sourceLayer"], "sop_arbitration")
        self.assertEqual(rejected_switch["activeTask"]["sopId"], "refund_ticket")


def _new_session(client: TestClient) -> int:
    return int(client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"])


def _message(client: TestClient, session_id: int, message: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200, response.text
    return dict(response.json()["data"])


def _matrix_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(
        RuntimeLabRepository(session),
        faq_answer_gate=_MatrixExactFaqGate(),
        faq_semantic_gate=_MatrixSemanticFaqGate(),
        rag_answer_gate=RagAnswerGate(
            _MatrixRagFacade(),
            knowledge_base_ids=[33],
            generator=FakeRagAnswerGenerator(),
            rerank=True,
        ),
        fallback_agent=_MatrixFallbackAgent(),
        agent_output_policy=AgentOutputPolicy(max_clarification_attempts=2),
    )


class _MatrixExactFaqGate:
    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        if message != "儿童票可以退吗":
            return None
        return FaqAnswerProposal(
            answer="儿童票符合客票规则时可以退，手续费以票规为准。",
            confidence=1.0,
            margin=1.0,
            evidence=FaqAnswerEvidence(
                faq_id=1,
                question="儿童票可以退吗",
                answer="儿童票符合客票规则时可以退，手续费以票规为准。",
                score=2.0,
                match_type="EXACT",
                source="structured_faq",
                matched_terms=("儿童票可以退吗",),
                knowledge_base_id=33,
            ),
        )


class _MatrixSemanticFaqGate:
    def decide(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        del active_task, suspended_tasks
        if message != "小朋友的票能不能退回来":
            return None
        return RouteDecision(
            action="ANSWER_FAQ",
            reason="Semantic FAQ accepted before SOP arbitration",
            faq_answer={
                "sourceLayer": "faq_semantic",
                "reasonCode": "SEMANTIC_HIGH_CONFIDENCE",
                "answer": "儿童票可以按客票规则申请退票。",
                "confidence": 0.93,
                "margin": 0.2,
                "mutatesSopState": False,
                "evidence": {
                    "retrievalMode": "faq",
                    "rerankUsed": True,
                    "topFaqs": [{"faqId": 2, "score": 0.93, "matchType": "VECTOR"}],
                },
            },
        )


class _MatrixRagFacade:
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list["_MatrixRagHit"]:
        del knowledge_base_id, top_k, retrieval_mode, score_threshold, rerank
        if query in {"航班延误超过4小时保险怎么赔？", "航班延误保险怎么赔？"}:
            return [
                _MatrixRagHit(
                    chunk_id=70,
                    content="航班延误超过 4 小时，可提交延误证明、登机牌、保单和身份证明材料申请赔付。",
                    score=0.92,
                )
            ]
        return []


class _MatrixRagHit:
    source_type = "DOCUMENT_CHUNK"
    match_type = "VECTOR"
    title = "航班延误险条款"
    document_id = 7
    chunk_index = 0

    def __init__(self, chunk_id: int, content: str, score: float) -> None:
        self.chunk_id = chunk_id
        self.content = content
        self.score = score


class _MatrixFallbackAgent:
    def run(self, request: FallbackAgentRequest) -> FallbackAgentOutput:
        if request.message in {"外星权益", "不知道", "还是那个"}:
            return FallbackAgentOutput(
                response_type="clarification",
                clarification_question="请补充您要咨询的问题背景，或说明希望办理的业务。",
                confidence=0.51,
            )
        if "赔付争议材料" in request.message:
            return FallbackAgentOutput(
                response_type="handoff_recommendation",
                answer="建议转人工处理。",
                handoff_reason="Agent judged request requires human review",
                confidence=0.89,
            )
        return FallbackAgentOutput(
            response_type="answer",
            answer=f"我先帮您整理诉求：{request.message}。",
            confidence=0.7,
        )
