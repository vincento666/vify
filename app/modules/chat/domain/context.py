from collections.abc import MutableMapping, Sequence
from typing import Any, Protocol

MessageContext = dict[str, str]


class MessageRepository(Protocol):
    def list_messages(
        self,
        session_id: int,
        page: int,
        page_size: int,
    ) -> tuple[list[dict[str, Any]], int]:
        ...


def trim_context(messages: Sequence[MessageContext], max_messages: int) -> list[MessageContext]:
    if max_messages <= 0:
        return []
    return list(messages[-max_messages:])


class ConversationContextStore:
    def __init__(
        self,
        repository: MessageRepository,
        cache: MutableMapping[str, list[MessageContext]],
    ) -> None:
        self._repository = repository
        self._cache = cache

    def load(self, session_id: int, max_messages: int) -> list[MessageContext]:
        cache_key = self._cache_key(session_id)
        if cache_key not in self._cache:
            rows, _ = self._repository.list_messages(session_id, page=1, page_size=100)
            self._cache[cache_key] = [
                {"role": row["role"], "content": row["content"]}
                for row in rows
                if row["role"] in {"user", "assistant", "system"}
            ]
        return trim_context(self._cache[cache_key], max_messages)

    def append(self, session_id: int, messages: Sequence[MessageContext], max_messages: int) -> None:
        cache_key = self._cache_key(session_id)
        existing = self._cache.get(cache_key, [])
        self._cache[cache_key] = trim_context([*existing, *messages], max_messages)

    def evict(self, session_id: int) -> None:
        self._cache.pop(self._cache_key(session_id), None)

    def _cache_key(self, session_id: int) -> str:
        return f"chat:context:{session_id}"
