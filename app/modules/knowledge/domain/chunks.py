from __future__ import annotations

from dataclasses import dataclass
from itertools import count
import re
from threading import Lock


DEFAULT_CHUNK_MAX_CHARS = 500


@dataclass(frozen=True)
class ChunkRecord:
    id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int


_chunk_id_sequence = count(1)
_chunk_store: dict[int, list[ChunkRecord]] = {}
_chunk_store_lock = Lock()


def split_document_chunks(text: str, max_chars: int = DEFAULT_CHUNK_MAX_CHARS) -> list[str]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than 0")

    chunks: list[str] = []
    for paragraph in _paragraphs(text):
        if len(paragraph) <= max_chars:
            chunks.append(paragraph)
            continue
        chunks.extend(_fixed_size_chunks(paragraph, max_chars))
    return chunks


def estimate_token_count(content: str) -> int:
    words = re.findall(r"\S+", content)
    return max(1, len(words)) if content.strip() else 0


def decode_document_content(content: bytes) -> str:
    return content.decode("utf-8", errors="ignore")


def replace_document_chunks(document_id: int, text: str) -> list[ChunkRecord]:
    chunk_texts = split_document_chunks(text)
    records = [
        ChunkRecord(
            id=next(_chunk_id_sequence),
            document_id=document_id,
            chunk_index=index,
            content=chunk,
            token_count=estimate_token_count(chunk),
        )
        for index, chunk in enumerate(chunk_texts)
    ]
    with _chunk_store_lock:
        _chunk_store[document_id] = records
    return records


def list_document_chunks(document_id: int) -> list[ChunkRecord]:
    with _chunk_store_lock:
        return list(_chunk_store.get(document_id, []))


def clear_document_chunks(document_id: int) -> None:
    with _chunk_store_lock:
        _chunk_store.pop(document_id, None)


def _paragraphs(text: str) -> list[str]:
    return [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]


def _fixed_size_chunks(content: str, max_chars: int) -> list[str]:
    return [
        content[start : start + max_chars]
        for start in range(0, len(content), max_chars)
        if content[start : start + max_chars]
    ]
