from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
import math

from app.modules.knowledge.domain.chunks import ChunkRecord


@dataclass(frozen=True)
class EmbeddedChunk:
    chunk: ChunkRecord
    embedding: Sequence[float]


@dataclass(frozen=True)
class SimilarChunk:
    chunk: ChunkRecord
    score: float


def cosine_similarity(left: Sequence[float], right: Sequence[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right, strict=True))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm == 0.0 or right_norm == 0.0:
        return 0.0
    return dot / (left_norm * right_norm)


def rank_embedded_chunks(
    candidates: Sequence[EmbeddedChunk],
    query_embedding: Sequence[float],
    top_k: int,
) -> list[SimilarChunk]:
    if top_k <= 0:
        return []
    ranked = sorted(
        (
            SimilarChunk(
                chunk=candidate.chunk,
                score=cosine_similarity(candidate.embedding, query_embedding),
            )
            for candidate in candidates
        ),
        key=lambda result: (-result.score, result.chunk.chunk_index, result.chunk.id),
    )
    return ranked[:top_k]
