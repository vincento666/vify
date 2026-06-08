import unittest

from app.modules.runtime_lab.domain.payload import format_route_decision
from app.modules.runtime_lab.domain.router import RouteDecision


class RagAnswerContractTest(unittest.TestCase):
    def test_answer_rag_route_decision_payload_exposes_citations_and_generation_evidence(self) -> None:
        payload = format_route_decision(
            RouteDecision(
                action="ANSWER_RAG",
                reason="RAG answer accepted after SOP arbitration",
                rag_answer={
                    "sourceLayer": "rag_policy",
                    "reasonCode": "RAG_HIGH_CONFIDENCE",
                    "answer": "延误超过 4 小时可按保险条款申请理赔。",
                    "confidence": 0.86,
                    "mutatesSopState": False,
                    "citations": [{"sourceId": "chunk:7", "title": "延误险条款", "score": 0.91}],
                    "retrievalEvidence": {"retrievalMode": "hybrid", "topChunks": []},
                    "generationEvidence": {"mode": "fake", "model": "fake-rag-generator"},
                },
            )
        )

        self.assertEqual(payload["action"], "ANSWER_RAG")
        self.assertEqual(payload["ragAnswer"]["sourceLayer"], "rag_policy")
        self.assertEqual(payload["ragAnswer"]["reasonCode"], "RAG_HIGH_CONFIDENCE")
        self.assertFalse(payload["ragAnswer"]["mutatesSopState"])
        self.assertEqual(payload["ragAnswer"]["citations"][0]["sourceId"], "chunk:7")
        self.assertEqual(payload["finalDecision"]["sourceLayer"], "rag_policy")
        self.assertEqual(payload["finalDecision"]["reasonCode"], "RAG_HIGH_CONFIDENCE")

    def test_fake_rag_generator_uses_context_and_returns_citations(self) -> None:
        from app.modules.runtime_lab.domain.rag_gate import FakeRagAnswerGenerator, RagContext

        result = FakeRagAnswerGenerator().generate(
            "航班延误超过 4 小时保险怎么赔？",
            contexts=[
                RagContext(
                    source_id="chunk:7",
                    title="延误险条款",
                    content="航班延误超过 4 小时，可提交保险理赔申请。",
                    score=0.91,
                )
            ],
        )

        self.assertIn("航班延误超过 4 小时", result.answer)
        self.assertEqual(result.citations[0]["sourceId"], "chunk:7")
        self.assertEqual(result.generation_evidence["mode"], "fake")
