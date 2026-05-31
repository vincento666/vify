from __future__ import annotations

from collections.abc import Iterator, Sequence
import hashlib
import math
import re

from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS


FAKE_EMBEDDING_MODEL = "fake-local-hash-v1"


class EmbeddingBatcher:
    def __init__(self, batch_size: int = 16) -> None:
        if batch_size <= 0:
            raise ValueError("batch_size must be greater than 0")
        self._batch_size = batch_size

    def iter_batches(self, texts: Sequence[str]) -> Iterator[list[str]]:
        for start in range(0, len(texts), self._batch_size):
            yield list(texts[start : start + self._batch_size])


class FakeEmbeddingProvider:
    model_name = FAKE_EMBEDDING_MODEL

    def __init__(self, dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS) -> None:
        if dimensions <= 0:
            raise ValueError("dimensions must be greater than 0")
        self.dimensions = dimensions

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        return [self._embed_one(text) for text in texts]

    def _embed_one(self, text: str) -> list[float]:
        terms = _terms(text) or [text.strip().lower()]
        values = [0.0] * self.dimensions
        for term in terms:
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values))
        if norm == 0.0:
            return values
        return [round(value / norm, 6) for value in values]


def _terms(text: str) -> list[str]:
    return re.findall(r"[0-9a-zA-Z_\u4e00-\u9fff]+", text.lower())
