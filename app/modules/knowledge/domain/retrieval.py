from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum
import os
from typing import Any, Generic, Protocol, TypeVar

import httpx


class RetrievalMode(StrEnum):
    AUTO = "auto"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"
    KEYWORD = "keyword"
    FAQ = "faq"


@dataclass(frozen=True)
class RetrievalOptions:
    mode: RetrievalMode = RetrievalMode.AUTO
    top_k: int = 3
    min_score: float = 0.0
    rerank: bool = False

    @classmethod
    def from_request(
        cls,
        retrieval_mode: str | RetrievalMode | None = None,
        top_k: int | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> RetrievalOptions:
        return cls(
            mode=_normalize_mode(retrieval_mode),
            top_k=max(1, int(top_k or 3)),
            min_score=max(0.0, float(score_threshold or 0.0)),
            rerank=bool(rerank),
        )

    @property
    def effective_mode(self) -> RetrievalMode:
        if self.mode == RetrievalMode.AUTO:
            return RetrievalMode.HYBRID
        return self.mode


T = TypeVar("T")


@dataclass(frozen=True)
class FusedRankEntry(Generic[T]):
    item: T
    score: float


@dataclass(frozen=True)
class RerankCandidate:
    id: str
    text: str
    score: float = 0.0
    metadata: dict[str, Any] | None = None


class CandidateReranker(Protocol):
    def rerank(
        self,
        query: str,
        candidates: Sequence[RerankCandidate],
        top_k: int,
    ) -> list[RerankCandidate]:
        ...


class RrfReranker:
    def rerank_rankings(
        self,
        query: str,
        rankings: Sequence[Sequence[T]],
        top_k: int,
    ) -> list[FusedRankEntry[T]]:
        return reciprocal_rank_fuse(rankings, top_k)


class HttpReranker:
    def __init__(
        self,
        *,
        endpoint: str,
        api_key: str = "",
        http_client: httpx.Client | None = None,
    ) -> None:
        if not endpoint:
            raise ValueError("endpoint is required")
        self.endpoint = endpoint
        self.api_key = api_key
        self._client = http_client or httpx.Client(timeout=20.0)

    def rerank(
        self,
        query: str,
        candidates: Sequence[RerankCandidate],
        top_k: int,
    ) -> list[RerankCandidate]:
        if top_k <= 0 or not candidates:
            return []
        headers = {"Authorization": f"Bearer {self.api_key}"} if self.api_key else {}
        response = self._client.post(
            self.endpoint,
            headers=headers,
            json={
                "query": query,
                "topK": top_k,
                "documents": [
                    {
                        "id": candidate.id,
                        "text": candidate.text,
                        "score": candidate.score,
                        "metadata": candidate.metadata or {},
                    }
                    for candidate in candidates
                ],
            },
        )
        response.raise_for_status()
        payload = response.json()
        by_id = {candidate.id: candidate for candidate in candidates}
        ranked: list[RerankCandidate] = []
        results = payload.get("results") if isinstance(payload, dict) else None
        for result in results if isinstance(results, list) else []:
            if not isinstance(result, dict):
                continue
            candidate_id = str(result.get("id") or "")
            candidate = by_id.get(candidate_id)
            if candidate is None:
                continue
            ranked.append(
                RerankCandidate(
                    id=candidate.id,
                    text=candidate.text,
                    score=float(result.get("score") or candidate.score),
                    metadata=candidate.metadata,
                )
            )
        seen = {candidate.id for candidate in ranked}
        ranked.extend(candidate for candidate in candidates if candidate.id not in seen)
        return ranked[:top_k]


def create_reranker(config: dict[str, Any] | None = None) -> CandidateReranker | None:
    values = dict(config or {})
    provider = str(values.get("provider") or os.getenv("HIFY_RERANKER_PROVIDER") or "").lower()
    if provider == "http":
        endpoint = str(values.get("endpoint") or os.getenv("HIFY_RERANKER_ENDPOINT") or "")
        if not endpoint:
            return None
        return HttpReranker(
            endpoint=endpoint,
            api_key=str(values.get("api_key") or os.getenv("HIFY_RERANKER_API_KEY") or ""),
            http_client=values.get("http_client"),
        )
    return None


def reciprocal_rank_fuse(
    rankings: Sequence[Sequence[T]],
    top_k: int,
    *,
    rank_constant: int = 60,
    weights: Sequence[float] | None = None,
) -> list[FusedRankEntry[T]]:
    if top_k <= 0:
        return []
    weighted_rankings = list(rankings)
    ranking_weights = list(weights or [1.0] * len(weighted_rankings))
    scores: dict[T, float] = {}
    first_seen: dict[T, tuple[int, int]] = {}
    for ranking_index, ranking in enumerate(weighted_rankings):
        weight = ranking_weights[ranking_index] if ranking_index < len(ranking_weights) else 1.0
        for zero_rank, item in enumerate(ranking):
            rank = zero_rank + 1
            scores[item] = scores.get(item, 0.0) + weight / (rank_constant + rank)
            first_seen.setdefault(item, (ranking_index, zero_rank))
    ranked = sorted(
        scores.items(),
        key=lambda item_score: (-item_score[1], first_seen[item_score[0]], str(item_score[0])),
    )
    return [FusedRankEntry(item=item, score=score) for item, score in ranked[:top_k]]


def _normalize_mode(value: str | RetrievalMode | None) -> RetrievalMode:
    if isinstance(value, RetrievalMode):
        return value
    normalized = str(value or RetrievalMode.AUTO.value).strip().lower()
    try:
        return RetrievalMode(normalized)
    except ValueError:
        return RetrievalMode.AUTO
