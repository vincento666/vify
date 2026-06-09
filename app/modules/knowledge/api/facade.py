from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from sqlalchemy.orm import Session

from app.modules.knowledge.domain.embeddings import create_embedding_provider
from app.modules.knowledge.domain.retrieval import (
    CandidateReranker,
    RerankCandidate,
    RetrievalMode,
    RetrievalOptions,
    create_reranker,
    reciprocal_rank_fuse,
)
from app.modules.knowledge.domain.search import keyword_confidence, rank_chunks, score_chunk
from app.modules.knowledge.domain.vector_store import RepositoryVectorStore, VectorStore, create_vector_store
from app.modules.knowledge.infra.repository import KnowledgeBaseRepository

KEYWORD_CONFIDENCE_THRESHOLD = 0.6


@dataclass(frozen=True)
class KnowledgeSearchResult:
    chunk_id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int
    score: float
    source_type: str = "DOCUMENT_CHUNK"
    match_type: str = "VECTOR"
    title: str = ""
    answer: str = ""
    faq_id: int = 0


@dataclass(frozen=True)
class KnowledgeContextResult:
    source_type: str
    match_type: str
    score: float
    title: str
    content: str
    answer: str = ""
    faq_id: int = 0
    document_id: int = 0
    chunk_id: int = 0
    chunk_index: int = 0
    metadata: dict[str, Any] | None = None


class KnowledgeFacade:
    def __init__(self, session: Session) -> None:
        self._repository = KnowledgeBaseRepository(session)
        self._embedding_provider = create_embedding_provider()
        self._vector_store: VectorStore = create_vector_store(self._repository)
        self._reranker = create_reranker()

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[KnowledgeSearchResult]:
        context_results = self.search_context(
            knowledge_base_id,
            query,
            top_k=top_k,
            retrieval_mode=retrieval_mode,
            score_threshold=score_threshold,
            rerank=rerank,
        )
        return [
            KnowledgeSearchResult(
                chunk_id=result.chunk_id,
                document_id=result.document_id,
                chunk_index=result.chunk_index,
                content=result.answer or result.content,
                token_count=max(1, len((result.answer or result.content).split())),
                score=result.score,
                source_type=result.source_type,
                match_type=result.match_type,
                title=result.title,
                answer=result.answer,
                faq_id=result.faq_id,
            )
            for result in context_results
        ]

    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
        options: RetrievalOptions | None = None,
    ) -> list[KnowledgeContextResult]:
        retrieval_options = options or RetrievalOptions.from_request(
            retrieval_mode=retrieval_mode,
            top_k=top_k,
            score_threshold=score_threshold,
            rerank=rerank,
        )
        if retrieval_options.top_k <= 0 or self._repository.get(knowledge_base_id) is None:
            return []
        mode = retrieval_options.effective_mode
        query_embedding: list[float] | None = None
        vector_results: list[KnowledgeContextResult] = []
        keyword_results: list[KnowledgeContextResult] = []
        faq_results: list[KnowledgeContextResult] = []

        if mode in {RetrievalMode.SEMANTIC, RetrievalMode.HYBRID}:
            query_embedding = self._embedding_provider.embed([query])[0]
            vector_results = [
                KnowledgeContextResult(
                    source_type="DOCUMENT_CHUNK",
                    match_type="VECTOR",
                    score=result.score,
                    title=f"Document #{result.chunk.document_id} chunk #{result.chunk.chunk_index + 1}",
                    content=result.chunk.content,
                    chunk_id=result.chunk.id,
                    document_id=result.chunk.document_id,
                    chunk_index=result.chunk.chunk_index,
                )
                for result in self._get_vector_store().search_chunks(
                    knowledge_base_id,
                    query_embedding,
                    self._embedding_provider.model_name,
                    retrieval_options.top_k,
                )
            ]
        if mode in {RetrievalMode.KEYWORD, RetrievalMode.HYBRID}:
            keyword_results = self._keyword_results(knowledge_base_id, query, retrieval_options.top_k)
        if mode in {RetrievalMode.FAQ, RetrievalMode.KEYWORD, RetrievalMode.HYBRID}:
            faq_results = self._faq_results(knowledge_base_id, query)
        if mode in {RetrievalMode.FAQ, RetrievalMode.HYBRID}:
            if query_embedding is None:
                query_embedding = self._embedding_provider.embed([query])[0]
            faq_results = [
                *faq_results,
                *self._faq_vector_results(
                    knowledge_base_id,
                    query_embedding,
                    retrieval_options.top_k,
                ),
            ]

        fusion_scores = _fusion_scores([faq_results, keyword_results, vector_results]) if mode == RetrievalMode.HYBRID else {}
        merged = merge_context_results(
            [*faq_results, *keyword_results, *vector_results],
            retrieval_options.top_k,
            fusion_scores=fusion_scores,
        )
        if retrieval_options.min_score > 0:
            merged = [result for result in merged if result.score >= retrieval_options.min_score]
        if retrieval_options.rerank:
            merged = self._rerank_results(query, merged, retrieval_options.top_k)
        return merged[: retrieval_options.top_k]

    def _keyword_results(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
    ) -> list[KnowledgeContextResult]:
        chunks = [
            chunk
            for document in self._repository.list_done_documents(knowledge_base_id)
            for chunk in self._repository.list_document_chunks(int(document["id"]))
        ]
        results: list[KnowledgeContextResult] = []
        for chunk in rank_chunks(chunks, query, top_k):
            keyword_score = score_chunk(chunk, query)
            confidence = keyword_confidence(chunk, query)
            if keyword_score <= 0 or confidence < KEYWORD_CONFIDENCE_THRESHOLD:
                continue
            results.append(
                KnowledgeContextResult(
                    source_type="DOCUMENT_CHUNK",
                    match_type="KEYWORD",
                    score=1.0 + confidence * 0.01,
                    title=f"Document #{chunk.document_id} chunk #{chunk.chunk_index + 1}",
                    content=chunk.content,
                    chunk_id=chunk.id,
                    document_id=chunk.document_id,
                    chunk_index=chunk.chunk_index,
                )
            )
        return results

    def _faq_results(self, knowledge_base_id: int, query: str) -> list[KnowledgeContextResult]:
        normalized_query = _normalize_text(query)
        query_tokens = _tokens(query)
        results: list[KnowledgeContextResult] = []
        for faq in self._repository.list_enabled_faqs(knowledge_base_id):
            question = str(faq.get("question") or "")
            answer = str(faq.get("answer") or "")
            alternatives = _as_string_list(faq.get("alternative_questions"))
            keywords = _as_string_list(faq.get("keywords"))
            candidates = [question, *alternatives]
            normalized_candidates = [_normalize_text(candidate) for candidate in candidates]
            priority_boost = min(0.2, max(0, int(faq.get("priority") or 0)) * 0.005)

            if normalized_query and normalized_query in normalized_candidates:
                match_type = "EXACT"
                score = 2.0 + priority_boost
            else:
                keyword_overlap = len(query_tokens & set(_normalize_text(keyword) for keyword in keywords))
                semantic_overlap = max((_overlap_ratio(query_tokens, _tokens(candidate)) for candidate in candidates), default=0.0)
                if keyword_overlap > 0:
                    match_type = "KEYWORD" if semantic_overlap < 0.5 else "HYBRID"
                    score = 1.2 + keyword_overlap * 0.1 + semantic_overlap * 0.1 + priority_boost
                elif semantic_overlap >= 0.5:
                    match_type = "VECTOR"
                    score = 0.95 + semantic_overlap * 0.2 + priority_boost
                else:
                    continue

            results.append(
                KnowledgeContextResult(
                    source_type="FAQ",
                    match_type=match_type,
                    score=score,
                    title=question,
                    content=question,
                    answer=answer,
                    faq_id=int(faq["id"]),
                    metadata=dict(faq.get("metadata") or {}),
                )
            )
        return results

    def _faq_vector_results(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        top_k: int,
    ) -> list[KnowledgeContextResult]:
        return [
            KnowledgeContextResult(
                source_type="FAQ",
                match_type="VECTOR",
                score=result.score,
                title=str(result.faq.get("question") or ""),
                content=str(result.faq.get("question") or ""),
                answer=str(result.faq.get("answer") or ""),
                faq_id=int(result.faq["id"]),
                metadata=dict(result.faq.get("metadata") or {}),
            )
            for result in self._get_vector_store().search_faqs(
                knowledge_base_id,
                query_embedding,
                self._embedding_provider.model_name,
                top_k,
            )
        ]

    def _get_vector_store(self) -> VectorStore:
        return getattr(self, "_vector_store", RepositoryVectorStore(self._repository))

    def _rerank_results(
        self,
        query: str,
        results: list[KnowledgeContextResult],
        top_k: int,
    ) -> list[KnowledgeContextResult]:
        reranker = self._get_reranker()
        if reranker is None or not results:
            return results[:top_k]
        by_id = {_candidate_id(result): result for result in results}
        candidates = [
            RerankCandidate(
                id=_candidate_id(result),
                text=result.answer or result.content,
                score=result.score,
                metadata={"sourceType": result.source_type, "matchType": result.match_type},
            )
            for result in results
        ]
        ranked = reranker.rerank(query, candidates, top_k)
        reranked: list[KnowledgeContextResult] = []
        for candidate in ranked:
            result = by_id.get(candidate.id)
            if result is None:
                continue
            reranked.append(_with_score(result, candidate.score))
        seen = {_candidate_id(result) for result in reranked}
        reranked.extend(result for result in results if _candidate_id(result) not in seen)
        return reranked[:top_k]

    def _get_reranker(self) -> CandidateReranker | None:
        return getattr(self, "_reranker", None)


def merge_context_results(
    results: list[KnowledgeContextResult],
    top_k: int,
    fusion_scores: dict[tuple[str, int], float] | None = None,
) -> list[KnowledgeContextResult]:
    merged: dict[tuple[str, int], KnowledgeContextResult] = {}
    fusion_scores = fusion_scores or {}
    for result in results:
        key = _result_key(result)
        adjusted = _with_score(result, result.score + fusion_scores.get(key, 0.0))
        current = merged.get(key)
        if current is None or adjusted.score > current.score:
            merged[key] = adjusted
        if current is not None and current.match_type != adjusted.match_type:
            best = merged[key]
            merged[key] = KnowledgeContextResult(
                source_type=best.source_type,
                match_type="HYBRID",
                score=max(current.score, adjusted.score),
                title=best.title,
                content=best.content,
                answer=best.answer,
                faq_id=best.faq_id,
                document_id=best.document_id,
                chunk_id=best.chunk_id,
                chunk_index=best.chunk_index,
                metadata=best.metadata,
            )
    return sorted(
        merged.values(),
        key=lambda result: (
            -result.score,
            0 if result.source_type == "FAQ" else 1,
            result.chunk_index,
            result.faq_id or result.chunk_id,
        ),
    )[:top_k]


def _fusion_scores(rankings: list[list[KnowledgeContextResult]]) -> dict[tuple[str, int], float]:
    ranked_keys = [[_result_key(result) for result in ranking] for ranking in rankings if ranking]
    return {entry.item: entry.score for entry in reciprocal_rank_fuse(ranked_keys, top_k=1000)}


def _result_key(result: KnowledgeContextResult) -> tuple[str, int]:
    return (result.source_type, result.faq_id if result.source_type == "FAQ" else result.chunk_id)


def _candidate_id(result: KnowledgeContextResult) -> str:
    source_type, source_id = _result_key(result)
    return f"{source_type}:{source_id}"


def _with_score(result: KnowledgeContextResult, score: float) -> KnowledgeContextResult:
    return KnowledgeContextResult(
        source_type=result.source_type,
        match_type=result.match_type,
        score=score,
        title=result.title,
        content=result.content,
        answer=result.answer,
        faq_id=result.faq_id,
        document_id=result.document_id,
        chunk_id=result.chunk_id,
        chunk_index=result.chunk_index,
        metadata=result.metadata,
    )


def _as_string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def _normalize_text(value: str) -> str:
    return " ".join(str(value or "").strip().lower().split())


def _tokens(value: str) -> set[str]:
    return {token for token in re.split(r"\W+", _normalize_text(value)) if token}


def _overlap_ratio(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / max(1, min(len(left), len(right)))
