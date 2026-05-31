import unittest

try:
    from app.modules.knowledge.domain.chunks import estimate_token_count, split_document_chunks
except ModuleNotFoundError:
    estimate_token_count = None  # type: ignore[assignment]
    split_document_chunks = None  # type: ignore[assignment]


class ChunkSplitterTest(unittest.TestCase):
    def test_splits_non_empty_paragraphs_in_order(self) -> None:
        self.assertIsNotNone(split_document_chunks)

        chunks = split_document_chunks("Intro\n\nUsage guide\n\nFAQ", max_chars=80)

        self.assertEqual(chunks, ["Intro", "Usage guide", "FAQ"])

    def test_splits_long_paragraphs_by_character_limit(self) -> None:
        self.assertIsNotNone(split_document_chunks)

        chunks = split_document_chunks("abcdefghij", max_chars=4)

        self.assertEqual(chunks, ["abcd", "efgh", "ij"])

    def test_estimates_tokens_from_words_and_never_returns_zero_for_content(self) -> None:
        self.assertIsNotNone(estimate_token_count)

        self.assertEqual(estimate_token_count("alpha beta"), 2)
        self.assertEqual(estimate_token_count("中文内容"), 1)


if __name__ == "__main__":
    unittest.main()
