from __future__ import annotations

from collections.abc import Iterator, Sequence
import hashlib
import math
import os
import re
from typing import Any, Protocol

import httpx

from app.core.schema import DEFAULT_EMBEDDING_DIMENSIONS


FAKE_EMBEDDING_MODEL = "fake-local-hash-v1"


class EmbeddingProvider(Protocol):
    model_name: str
    dimensions: int

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        ...


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


class OpenRouterEmbeddingProvider:
    def __init__(
        self,
        api_key: str,
        model_name: str,
        *,
        base_url: str = "https://openrouter.ai/api/v1",
        http_client: httpx.Client | None = None,
        dimensions: int = DEFAULT_EMBEDDING_DIMENSIONS,
    ) -> None:
        if not api_key:
            raise ValueError("api_key is required")
        if not model_name:
            raise ValueError("model_name is required")
        self.api_key = api_key
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.dimensions = dimensions
        self._client = http_client or httpx.Client(timeout=30.0)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self._client.post(
            f"{self.base_url}/embeddings",
            headers={"Authorization": f"Bearer {self.api_key}"},
            json={"model": self.model_name, "input": list(texts)},
        )
        response.raise_for_status()
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, list):
            raise ValueError("OpenRouter embeddings response missing data")
        embeddings: list[list[float]] = []
        for item in data:
            embedding = item.get("embedding") if isinstance(item, dict) else None
            if not isinstance(embedding, list):
                raise ValueError("OpenRouter embeddings response missing embedding")
            embeddings.append([float(value) for value in embedding])
        return embeddings


class LocalSentenceTransformerEmbeddingProvider:
    def __init__(
        self,
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
        *,
        model_loader: Any | None = None,
        dimensions: int = 384,
    ) -> None:
        if not model_name:
            raise ValueError("model_name is required")
        self.model_name = model_name
        self.dimensions = dimensions
        if model_loader is None:
            try:
                from sentence_transformers import SentenceTransformer  # type: ignore[import-not-found]
            except ImportError as exc:
                raise ImportError(
                    "sentence-transformers is required for local-hf embeddings"
                ) from exc
            model_loader = SentenceTransformer
        self._model = model_loader(model_name)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        encoded = self._model.encode(list(texts), normalize_embeddings=True)
        return [[float(value) for value in row] for row in encoded]


def create_embedding_provider(config: dict[str, Any] | None = None) -> EmbeddingProvider:
    values = dict(config or {})
    provider = str(
        values.get("provider") or os.getenv("HIFY_EMBEDDING_PROVIDER") or ""
    ).lower()
    api_key = str(values.get("api_key") or os.getenv("OPENROUTER_API_KEY") or "")
    configured_model = values.get("model") or values.get("model_name")
    openrouter_model_name = str(
        configured_model
        or os.getenv("HIFY_OPENROUTER_EMBEDDING_MODEL")
        or ""
    )
    local_model_name = str(
        configured_model
        or os.getenv("HIFY_LOCAL_EMBEDDING_MODEL")
        or os.getenv("HIFY_OPENROUTER_EMBEDDING_MODEL")
        or ""
    )
    if provider == "openrouter" and api_key and openrouter_model_name:
        return OpenRouterEmbeddingProvider(
            api_key=api_key,
            model_name=openrouter_model_name,
            base_url=str(values.get("base_url") or "https://openrouter.ai/api/v1"),
            dimensions=int(values.get("dimensions") or DEFAULT_EMBEDDING_DIMENSIONS),
        )
    if provider in {"local-hf", "local_hf", "sentence-transformers", "sentence_transformers"}:
        return LocalSentenceTransformerEmbeddingProvider(
            model_name=local_model_name or "sentence-transformers/all-MiniLM-L6-v2",
            model_loader=values.get("model_loader"),
            dimensions=int(values.get("dimensions") or 384),
        )
    return FakeEmbeddingProvider()


def _terms(text: str) -> list[str]:
    return re.findall(r"[0-9a-zA-Z_\u4e00-\u9fff]+", text.lower())
