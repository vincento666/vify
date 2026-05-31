import unittest
from typing import Any

try:
    from app.modules.chat.domain.context import ConversationContextStore, trim_context
except ModuleNotFoundError:
    ConversationContextStore = None  # type: ignore[assignment]
    trim_context = None  # type: ignore[assignment]


class ConversationContextStoreTest(unittest.TestCase):
    def test_trim_context_keeps_most_recent_messages(self) -> None:
        self.assertIsNotNone(trim_context)
        messages = [
            {"role": "user", "content": "one"},
            {"role": "assistant", "content": "two"},
            {"role": "user", "content": "three"},
        ]

        self.assertEqual(trim_context(messages, max_messages=2), messages[-2:])

    def test_load_uses_cache_before_repository_fallback(self) -> None:
        self.assertIsNotNone(ConversationContextStore)
        repository = _FakeMessageRepository()
        cache: dict[str, list[dict[str, str]]] = {}
        store = ConversationContextStore(repository, cache)

        first = store.load(session_id=1, max_messages=10)
        repository.rows = [{"role": "user", "content": "changed"}]
        second = store.load(session_id=1, max_messages=10)

        self.assertEqual(first, [{"role": "user", "content": "from db"}])
        self.assertEqual(second, first)
        self.assertEqual(repository.load_count, 1)


class _FakeMessageRepository:
    def __init__(self) -> None:
        self.rows: list[dict[str, Any]] = [{"role": "user", "content": "from db"}]
        self.load_count = 0

    def list_messages(
        self,
        session_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        self.load_count += 1
        return self.rows, len(self.rows)


if __name__ == "__main__":
    unittest.main()
