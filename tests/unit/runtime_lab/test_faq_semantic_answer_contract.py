import unittest


class FaqSemanticAnswerContractTest(unittest.TestCase):
    def test_semantic_gate_uses_faq_retrieval_and_emits_rerank_evidence(self) -> None:
        from app.modules.runtime_lab.domain.faq_gate import FaqSemanticAnswerGate

        facade = _RecordingKnowledgeFacade(
            [
                _KnowledgeHit(
                    source_type="FAQ",
                    match_type="VECTOR",
                    score=0.92,
                    title="儿童票退票规则",
                    answer="儿童票如未使用可按客票规则申请退票。",
                    faq_id=37,
                ),
                _KnowledgeHit(
                    source_type="FAQ",
                    match_type="VECTOR",
                    score=0.71,
                    title="婴儿票退票规则",
                    answer="婴儿票退票以客票规则为准。",
                    faq_id=38,
                ),
            ]
        )
        gate = FaqSemanticAnswerGate(facade, knowledge_base_ids=[33], rerank=True)

        decision = gate.decide("儿童机票能不能返钱？", active_task=None, suspended_tasks=[])

        assert decision is not None
        self.assertEqual(decision.action, "ANSWER_FAQ")
        self.assertEqual(decision.faq_answer["sourceLayer"], "faq_semantic")
        self.assertEqual(decision.faq_answer["reasonCode"], "SEMANTIC_HIGH_CONFIDENCE")
        self.assertFalse(decision.faq_answer["mutatesSopState"])
        evidence = decision.faq_answer["evidence"]
        self.assertEqual(evidence["faqId"], 37)
        self.assertEqual(evidence["matchType"], "VECTOR")
        self.assertEqual(evidence["retrievalMode"], "faq")
        self.assertTrue(evidence["rerankUsed"])
        self.assertEqual(evidence["topCandidates"][0]["faqId"], 37)
        self.assertEqual(
            facade.calls,
            [
                {
                    "knowledge_base_id": 33,
                    "query": "儿童机票能不能返钱？",
                    "top_k": 5,
                    "retrieval_mode": "faq",
                    "score_threshold": None,
                    "rerank": True,
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
