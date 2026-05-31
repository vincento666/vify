import unittest

from app.modules.knowledge.domain.chunks import ChunkRecord
from app.modules.knowledge.domain.vector_search import (
    EmbeddedChunk,
    cosine_similarity,
    rank_embedded_chunks,
)


class VectorSimilarityTest(unittest.TestCase):
    def test_cosine_similarity_scores_identical_vectors_highest(self) -> None:
        self.assertAlmostEqual(1.0, cosine_similarity([1.0, 0.0], [1.0, 0.0]))
        self.assertAlmostEqual(0.0, cosine_similarity([1.0, 0.0], [0.0, 1.0]))

    def test_rank_embedded_chunks_orders_by_cosine_score(self) -> None:
        candidates = [
            EmbeddedChunk(ChunkRecord(1, 10, 0, "Alpha", 1), [1.0, 0.0, 0.0]),
            EmbeddedChunk(ChunkRecord(2, 10, 1, "Beta", 1), [0.0, 1.0, 0.0]),
            EmbeddedChunk(ChunkRecord(3, 10, 2, "Gamma", 1), [0.0, 0.0, 1.0]),
        ]

        ranked = rank_embedded_chunks(candidates, [0.1, 0.9, 0.0], top_k=2)

        self.assertEqual([2, 1], [result.chunk.id for result in ranked])
        self.assertGreater(ranked[0].score, ranked[1].score)


if __name__ == "__main__":
    unittest.main()
