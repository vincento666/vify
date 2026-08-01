import unittest
from typing import Any
from unittest.mock import patch

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.agent_fallback import (
    AgentOutputPolicy,
    FallbackAgentOutput,
    FallbackAgentRequest,
)
from app.modules.runtime_lab.domain.faq_gate import RuntimeAirlineFaqGate
from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagAnswerGate
from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown
from app.modules.runtime_lab.domain.explicit_signals import ExplicitSignalDetector
from app.modules.runtime_lab.domain.recall import MockSemanticCandidateRecall
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service


class RuntimeLabConfusionRagAgentMatrixE2ETest(unittest.TestCase):
    def test_default_margin_clarifies_before_task_start(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _default_margin_runtime_service
        try:
            with (
                patch.object(ExplicitSignalDetector, "detect", return_value=[_margin_candidate("refund_ticket", 0.90)]),
                patch.object(MockSemanticCandidateRecall, "recall", return_value=[_margin_candidate("change_flight", 0.85)]),
                TestClient(app) as client,
            ):
                result = _send_one(client, "我想办理机票业务")
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(result["routeDecision"]["action"], "CLARIFY")
        self.assertIsNone(result["activeTask"])
        self.assertEqual(result["routeDecision"]["policyGate"]["candidateMargin"]["outcome"], "CLARIFY")

    def test_similar_faq_sop_rag_and_agent_queries_route_to_distinct_lanes(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _confusion_runtime_service
        try:
            with TestClient(app) as client:
                faq_cases = (
                    ("我不是要办理退票，就想问退票款多久到账？", "REFUND_ARRIVAL_TIME"),
                    ("先不改签，我只是问改签手续费怎么算？", "CHANGE_FEE_RULE"),
                    ("我不办宠物托运，只想知道宠物乘机需要什么材料？", "PET_CABIN_DOCS"),
                    ("不是要开发票，想问电子发票多久能开？", "INVOICE_TIMING"),
                    ("现在不值机，就问起飞前多久可以值机？", "CHECKIN_TIME"),
                )
                faq_results = [_send_one(client, message) for message, _ in faq_cases]

                sop_cases = (
                    ("我想办理退票，退票款多久到账也顺便看下", "refund_ticket"),
                    ("航班延误了，帮我改签到明天上午", "change_flight"),
                    ("别只给规则，我要给这张票加购20公斤托运行李", "baggage_service"),
                    ("我想现在就开发票，报销用", "invoice_apply"),
                    ("我带猫出行，帮我办理宠物乘机申请", "pet_cabin"),
                )
                sop_results = [_send_one(client, message) for message, _ in sop_cases]

                rag_cases = (
                    "我不办理改签，只想问航班延误超过4小时保险怎么赔？",
                    "航班取消后非自愿签转的资料通常包括哪些？",
                    "如果备降后要申请住宿补偿，需要准备哪些凭证？",
                    "延误险理赔材料和航司延误证明有什么区别？",
                    "航司取消航班后，现金补偿一般怎么判断？",
                )
                rag_results = [_send_one(client, message) for message in rag_cases]

                agent_cases = (
                    "机场大巴末班车几点",
                    "T3停车楼现在怎么收费",
                    "机场附近有没有能打印材料的地方",
                    "候机楼WiFi连不上怎么办",
                    "我这个说不清楚，还是那个问题",
                )
                agent_results = [_send_one(client, message) for message in agent_cases]

                active_session = _new_session(client)
                active_started = _message(client, active_session, "我要退票")
                active_rag_slot = _message(client, active_session, "航班延误保险怎么赔？订单TK-100")

                clarify_session = _new_session(client)
                _message(client, clarify_session, "我要退票")
                clarify_one = _message(client, clarify_session, "还是那个")
                clarify_two = _message(client, clarify_session, "不知道")
                escalated = _message(client, clarify_session, "随便")
        finally:
            app.dependency_overrides.pop(get_runtime_lab_service, None)

        for (message, reason_code), result in zip(faq_cases, faq_results, strict=True):
            with self.subTest(message=message):
                self.assertEqual(result["routeDecision"]["action"], "ANSWER_FAQ")
                self.assertEqual(result["routeDecision"]["faqAnswer"]["sourceLayer"], "runtime_airline_faq")
                self.assertEqual(result["routeDecision"]["faqAnswer"]["reasonCode"], reason_code)
                self.assertIsNone(result["activeTask"])

        for (message, sop_id), result in zip(sop_cases, sop_results, strict=True):
            with self.subTest(message=message):
                self.assertEqual(result["routeDecision"]["action"], "START_SOP")
                self.assertEqual(result["activeTask"]["sopId"], sop_id)
                self.assertIsNone(result["routeDecision"]["ragAnswer"])

        for message, result in zip(rag_cases, rag_results, strict=True):
            with self.subTest(message=message):
                self.assertEqual(result["routeDecision"]["action"], "ANSWER_RAG")
                self.assertEqual(result["routeDecision"]["ragAnswer"]["sourceLayer"], "rag_policy")
                self.assertEqual(result["routeDecision"]["ragAnswer"]["reasonCode"], "RAG_HIGH_CONFIDENCE")
                self.assertTrue(result["routeDecision"]["ragAnswer"]["citations"])
                self.assertIsNone(result["activeTask"])

        for message, result in zip(agent_cases, agent_results, strict=True):
            with self.subTest(message=message):
                self.assertIn(result["routeDecision"]["action"], {"AGENT_FALLBACK", "CLARIFY"})
                self.assertEqual(result["routeDecision"]["finalDecision"]["sourceLayer"], "agent_policy")
                self.assertIsNone(result["activeTask"])

        self.assertEqual(active_rag_slot["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(active_rag_slot["routeDecision"]["ragAnswer"]["reasonCode"], "RAG_ACTIVE_AMBIGUOUS")
        self.assertEqual(active_rag_slot["activeTask"]["id"], active_started["activeTask"]["id"])

        self.assertEqual(clarify_one["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(clarify_two["routeDecision"]["action"], "CLARIFY")
        self.assertEqual(escalated["routeDecision"]["action"], "HANDOFF_TO_HUMAN")
        self.assertEqual(escalated["routeDecision"]["handoff"]["reasonCode"], "CLARIFICATION_FAILED")


def _new_session(client: TestClient) -> int:
    response = client.post("/api/v1/runtime-lab/sessions")
    assert response.status_code == 200, response.text
    return int(response.json()["data"]["id"])


def _send_one(client: TestClient, message: str) -> dict[str, Any]:
    return _message(client, _new_session(client), message)


def _message(client: TestClient, session_id: int, message: str) -> dict[str, Any]:
    response = client.post(
        f"/api/v1/runtime-lab/sessions/{session_id}/messages",
        json={"message": message},
    )
    assert response.status_code == 200, response.text
    return dict(response.json()["data"])


def _confusion_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(
        RuntimeLabRepository(session),
        faq_answer_gate=RuntimeAirlineFaqGate(),
        rag_answer_gate=RagAnswerGate(
            _ConfusionRagFacade(),
            knowledge_base_ids=[34],
            generator=FakeRagAnswerGenerator(),
            rerank=True,
        ),
        fallback_agent=_ConfusionFallbackAgent(),
        agent_output_policy=AgentOutputPolicy(max_clarification_attempts=2),
        policy_thresholds={"candidateMinMargin": 0.0},
    )


def _default_margin_runtime_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    return RuntimeLabService(RuntimeLabRepository(session))


def _margin_candidate(target_id: str, score: float) -> RouteCandidate:
    return RouteCandidate(
        candidate_id=f"sop:{target_id}",
        candidate_type=CandidateType.SOP_INTENT,
        target_id=target_id,
        display_name=target_id,
        source="margin_e2e_fixture",
        score=score,
        score_breakdown=ScoreBreakdown(keyword=score, alias=0.0, semantic=0.0),
        matched_terms=(target_id,),
        risk_level="LOW",
        requires_classifier=True,
        reason="candidate margin e2e fixture",
    )


class _ConfusionRagFacade:
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list["_ConfusionRagHit"]:
        del knowledge_base_id, top_k, retrieval_mode, score_threshold, rerank
        if any(term in query for term in ("延误", "取消", "备降", "签转", "补偿", "理赔")):
            return [
                _ConfusionRagHit(
                    chunk_id=9101,
                    title="异常航班保障与理赔材料",
                    content=(
                        "航班延误、取消或备降后，旅客通常可准备延误证明、登机牌、"
                        "保单、住宿或交通凭证等材料，用于保险理赔、非自愿签转或补偿咨询。"
                    ),
                    score=0.92,
                )
            ]
        return []


class _ConfusionRagHit:
    source_type = "DOCUMENT_CHUNK"
    match_type = "VECTOR"
    document_id = 91
    chunk_index = 0

    def __init__(self, *, chunk_id: int, title: str, content: str, score: float) -> None:
        self.chunk_id = chunk_id
        self.title = title
        self.content = content
        self.score = score


class _ConfusionFallbackAgent:
    def run(self, request: FallbackAgentRequest) -> FallbackAgentOutput:
        if request.message in {"还是那个", "不知道", "随便"}:
            return FallbackAgentOutput(
                response_type="clarification",
                clarification_question="请补充您要查询还是办理，以及对应航班或订单背景。",
                confidence=0.52,
            )
        return FallbackAgentOutput(
            response_type="answer",
            answer=f"我先按通用出行咨询整理：{request.message}。建议以机场或航司官方渠道为准。",
            confidence=0.72,
        )
