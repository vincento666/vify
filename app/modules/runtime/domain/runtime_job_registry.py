from __future__ import annotations

from collections.abc import Callable
from typing import Any


RuntimeJobHandler = Callable[[dict[str, Any]], None]


class RuntimeJobHandlerRegistry:
    def __init__(self) -> None:
        self._handlers: dict[str, RuntimeJobHandler] = {}

    @property
    def owner_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._handlers))

    def register(self, owner_type: str, handler: RuntimeJobHandler) -> None:
        normalized_owner = _normalize_owner_type(owner_type)
        if normalized_owner in self._handlers:
            raise ValueError(f"Runtime job handler already registered: {normalized_owner}")
        self._handlers[normalized_owner] = handler

    def handle(self, job: dict[str, Any]) -> None:
        owner_type = _normalize_owner_type(str(job.get("owner_type") or ""))
        try:
            handler = self._handlers[owner_type]
        except KeyError as exc:
            raise RuntimeError(f"No runtime job handler registered for owner: {owner_type}") from exc
        handler(job)


def _normalize_owner_type(owner_type: str) -> str:
    normalized = owner_type.strip().upper()
    if not normalized:
        raise ValueError("Runtime job owner type is required")
    return normalized
