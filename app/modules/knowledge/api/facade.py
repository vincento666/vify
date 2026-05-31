from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.modules.knowledge.domain.embeddings import FakeEmbeddingProvider
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository


@dataclass(frozen=True)
class KnowledgeSearchResult:
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int
    score: float


class KnowledgeFacade:
    def __init__(self, session: Session) -> None:
        self._repository = KnowledgeBaseRepository(session)
        self._embedding_provider = FakeEmbeddingProvider()

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
    ) -> list[KnowledgeSearchResult]:
        if top_k <= 0 or self._repository.get(knowledge_base_id) is None:
            return []
        query_embedding = self._embedding_provider.embed([query])[0]
        return [
            KnowledgeSearchResult(
                chunk_id=result.chunk.id,
                document_id=result.chunk.document_id,
                chunk_index=result.chunk.chunk_index,
                content=result.chunk.content,
                token_count=result.chunk.token_count,
                score=result.score,
            )
            for result in self._repository.search_similar_chunks(
                knowledge_base_id,
                query_embedding,
                self._embedding_provider.model_name,
                top_k,
            )
        ]
