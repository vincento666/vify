import unittest

try:
    from app.modules.knowledge.domain.chunks import ChunkRecord
    from app.modules.knowledge.domain.search import rank_chunks
except ModuleNotFoundError:
    ChunkRecord = None  # type: ignore[assignment]
    rank_chunks = None  # type: ignore[assignment]


class MockSearchTest(unittest.TestCase):
    def test_ranks_matching_chunks_before_non_matching_chunks(self) -> None:
        self.assertIsNotNone(ChunkRecord)
        self.assertIsNotNone(rank_chunks)
        chunks = [
            ChunkRecord(1, 10, 0, "Billing FAQ", 2),
            ChunkRecord(2, 10, 1, "How to reset password", 4),
            ChunkRecord(3, 10, 2, "Password support", 2),
        ]

        ranked = rank_chunks(chunks, "reset password", top_k=2)

        self.assertEqual([chunk.id for chunk in ranked], [2, 3])

    def test_uses_stable_query_hash_order_for_ties(self) -> None:
        self.assertIsNotNone(ChunkRecord)
        self.assertIsNotNone(rank_chunks)
        chunks = [
            ChunkRecord(1, 10, 0, "Alpha", 1),
            ChunkRecord(2, 10, 1, "Beta", 1),
            ChunkRecord(3, 10, 2, "Gamma", 1),
        ]

        first = rank_chunks(chunks, "unmatched", top_k=2)
        second = rank_chunks(chunks, "unmatched", top_k=2)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 2)


if __name__ == "__main__":
    unittest.main()
