import unittest

from app.modules.runtime_lab.domain.payload import format_route_decision
from app.modules.runtime_lab.domain.router import RouteDecision


class FaqExactAnswerContractTest(unittest.TestCase):
    def test_answer_faq_route_decision_payload_exposes_normalized_evidence(self) -> None:
        payload = format_route_decision(
            RouteDecision(
                action="ANSWER_FAQ",
                reason="Exact FAQ accepted before SOP arbitration",
                faq_answer={
                    "sourceLayer": "faq_exact",
                    "reasonCode": "EXACT_MATCH",
                    "answer": "儿童票如未使用可按客票规则申请退票。",
                    "confidence": 1.0,
                    "margin": 1.0,
                    "mutatesSopState": False,
                    "evidence": {
                        "faqId": 12,
                        "question": "儿童票可以退吗？",
                        "matchType": "EXACT",
                        "source": "structured_faq",
                    },
                },
            )
        )

        self.assertEqual(payload["action"], "ANSWER_FAQ")
        self.assertEqual(payload["faqAnswer"]["sourceLayer"], "faq_exact")
        self.assertEqual(payload["faqAnswer"]["reasonCode"], "EXACT_MATCH")
        self.assertFalse(payload["faqAnswer"]["mutatesSopState"])
        self.assertEqual(payload["faqAnswer"]["evidence"]["faqId"], 12)
        self.assertEqual(payload["finalDecision"]["action"], "ANSWER_FAQ")
        self.assertEqual(payload["finalDecision"]["sourceLayer"], "faq_exact")
        self.assertEqual(payload["finalDecision"]["reasonCode"], "EXACT_MATCH")

    def test_faq_answer_proposal_builds_route_decision_without_sop_mutation(self) -> None:
        from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal

        proposal = FaqAnswerProposal(
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

        decision = proposal.to_route_decision()

        self.assertEqual(decision.action, "ANSWER_FAQ")
        self.assertEqual(decision.reason, "Exact FAQ accepted before SOP arbitration")
        self.assertIsNone(decision.target_sop_id)
        self.assertIsNone(decision.active_task_id)
        self.assertFalse(decision.faq_answer["mutatesSopState"])
        self.assertEqual(decision.faq_answer["evidence"]["faqId"], 12)

    def test_faq_exact_gate_uses_knowledge_facade_keyword_faq_results(self) -> None:
        from app.modules.runtime_lab.domain.faq_gate import FaqExactAnswerGate

        facade = _RecordingKnowledgeFacade(
            [
                _KnowledgeHit(
                    source_type="FAQ",
                    match_type="EXACT",
                    score=2.0,
                    title="儿童票可以退吗？",
                    answer="儿童票如未使用可按客票规则申请退票。",
                    faq_id=12,
                )
            ]
        )
        gate = FaqExactAnswerGate(facade, knowledge_base_ids=[33])

        proposal = gate.propose("儿童票可以退吗？", active_task=None, suspended_tasks=[])

        assert proposal is not None
        self.assertEqual(proposal.answer, "儿童票如未使用可按客票规则申请退票。")
        self.assertEqual(proposal.evidence.faq_id, 12)
        self.assertEqual(proposal.evidence.match_type, "EXACT")
        self.assertEqual(proposal.evidence.source, "structured_faq")
        self.assertEqual(
            facade.calls,
            [
                {
                    "knowledge_base_id": 33,
                    "query": "儿童票可以退吗？",
                    "top_k": 3,
                    "retrieval_mode": "keyword",
                    "score_threshold": None,
                    "rerank": False,
                }
            ],
        )


class _KnowledgeHit:
    def __init__(
        self,
        *,
        source_type: str,
        match_type: str,
        score: float,
        title: str,
        answer: str,
        faq_id: int,
    ) -> None:
        self.source_type = source_type
        self.match_type = match_type
        self.score = score
        self.title = title
        self.answer = answer
        self.faq_id = faq_id


class _RecordingKnowledgeFacade:
    def __init__(self, hits: list[_KnowledgeHit]) -> None:
        self._hits = hits
        self.calls: list[dict[str, object]] = []

    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[_KnowledgeHit]:
        self.calls.append(
            {
                "knowledge_base_id": knowledge_base_id,
                "query": query,
                "top_k": top_k,
                "retrieval_mode": retrieval_mode,
                "score_threshold": score_threshold,
                "rerank": rerank,
            }
        )
        return self._hits
