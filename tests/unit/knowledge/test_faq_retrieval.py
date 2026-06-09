import unittest

from app.modules.knowledge.api.facade import KnowledgeContextResult, merge_context_results


class FaqRetrievalRankingTest(unittest.TestCase):
    def test_exact_faq_outranks_keyword_and_document_chunks(self) -> None:
        results = merge_context_results(
            [
                KnowledgeContextResult(
                    source_type="DOCUMENT_CHUNK",
                    match_type="VECTOR",
                    score=0.91,
                    title="doc",
                    content="Document chunk answer",
                    document_id=1,
                    chunk_id=2,
                ),
                KnowledgeContextResult(
                    source_type="FAQ",
                    match_type="KEYWORD",
                    score=1.15,
                    title="Refund keyword",
                    content="Refund keyword",
                    answer="Keyword answer",
                    faq_id=2,
                ),
                KnowledgeContextResult(
                    source_type="FAQ",
                    match_type="EXACT",
                    score=2.0,
                    title="How do I refund?",
                    content="How do I refund?",
                    answer="Exact answer",
                    faq_id=1,
                ),
            ],
            top_k=2,
        )

        self.assertEqual([result.source_type for result in results], ["FAQ", "FAQ"])
        self.assertEqual([result.match_type for result in results], ["EXACT", "KEYWORD"])
        self.assertEqual(results[0].answer, "Exact answer")


if __name__ == "__main__":
    unittest.main()
