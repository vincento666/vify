from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence

from app.modules.knowledge.domain.chunks import ChunkRecord


def rank_chunks(chunks: Sequence[ChunkRecord], query: str, top_k: int) -> list[ChunkRecord]:
    if top_k <= 0:
        return []
    normalized_query = query.strip().lower()
    ranked = sorted(
        chunks,
        key=lambda chunk: (
            -score_chunk(chunk, normalized_query),
            _stable_tie_key(chunk, normalized_query),
            chunk.chunk_index,
            chunk.id,
        ),
    )
    return ranked[:top_k]


def score_chunk(chunk: ChunkRecord, query: str) -> int:
    terms = set(_query_terms(query))
    if not terms:
        return 0
    content = chunk.content.lower()
    return sum(1 for term in terms if term in content)


def _query_terms(query: str) -> list[str]:
    return re.findall(r"[0-9a-zA-Z_\u4e00-\u9fff]+", query.lower())


def _stable_tie_key(chunk: ChunkRecord, query: str) -> str:
    payload = f"{query}|{chunk.id}|{chunk.chunk_index}|{chunk.content}".encode()
    return hashlib.sha256(payload).hexdigest()
