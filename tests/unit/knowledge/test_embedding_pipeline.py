import unittest

from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS
from app.modules.knowledge.domain.embeddings import EmbeddingBatcher, FakeEmbeddingProvider


class EmbeddingPipelineTest(unittest.TestCase):
    def test_batcher_splits_texts_by_batch_size(self) -> None:
        batcher = EmbeddingBatcher(batch_size=2)

        batches = list(batcher.iter_batches(["a", "b", "c"]))

        self.assertEqual([["a", "b"], ["c"]], batches)

    def test_fake_provider_returns_deterministic_vectors(self) -> None:
        provider = FakeEmbeddingProvider(dimensions=DEFAULT_EMBEDDING_DIMENSIONS)

        first = provider.embed(["Reset password", "Contact support"])
        second = provider.embed(["Reset password", "Contact support"])

        self.assertEqual(2, len(first))
        self.assertEqual(DEFAULT_EMBEDDING_DIMENSIONS, len(first[0]))
        self.assertEqual(first, second)
        self.assertNotEqual(first[0], first[1])
        self.assertTrue(all(-1.0 <= value <= 1.0 for value in first[0]))


if __name__ == "__main__":
    unittest.main()
