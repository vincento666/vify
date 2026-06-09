from __future__ import annotations

from collections.abc import Sequence
import os
from typing import Any, Protocol
import uuid

import httpx

from app.modules.knowledge.domain.chunks import ChunkRecord
from app.modules.knowledge.domain.vector_search import SimilarChunk, SimilarFaq


class VectorStore(Protocol):
    def search_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        ...

    def search_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarFaq]:
        ...

    def replace_document_embeddings(
        self,
        knowledge_base_id: int,
        chunks: Sequence[ChunkRecord],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        ...

    def replace_faq_embeddings(
        self,
        knowledge_base_id: int,
        faqs: Sequence[dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        ...


class RepositoryVectorStore:
    def __init__(self, repository: object) -> None:
        self._repository = repository

    def search_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        return self._repository.search_similar_chunks(  # type: ignore[attr-defined,no-any-return]
            knowledge_base_id,
            query_embedding,
            model_name,
            top_k,
        )

    def search_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarFaq]:
        return self._repository.search_similar_faqs(  # type: ignore[attr-defined,no-any-return]
            knowledge_base_id,
            query_embedding,
            model_name,
            top_k,
        )

    def replace_document_embeddings(
        self,
        knowledge_base_id: int,
        chunks: Sequence[ChunkRecord],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        return self._repository.replace_document_embeddings(  # type: ignore[attr-defined,no-any-return]
            chunks,
            embeddings,
            model_name,
            dimensions,
        )

    def replace_faq_embeddings(
        self,
        knowledge_base_id: int,
        faqs: Sequence[dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        return self._repository.replace_faq_embeddings(  # type: ignore[attr-defined,no-any-return]
            faqs,
            embeddings,
            model_name,
            dimensions,
        )


def create_vector_store(repository: object, config: dict[str, Any] | None = None) -> VectorStore:
    values = dict(config or {})
    provider = str(values.get("provider") or os.getenv("HIFY_VECTOR_STORE") or "pgvector").lower()
    if provider == "weaviate":
        return WeaviateVectorStore(
            base_url=str(values.get("base_url") or os.getenv("HIFY_WEAVIATE_URL") or ""),
            http_client=values.get("http_client"),
        )
    return RepositoryVectorStore(repository)


class WeaviateVectorStore:
    def __init__(
        self,
        *,
        base_url: str,
        http_client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._client = http_client or httpx.Client(timeout=10.0)

    def search_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        if not self.base_url:
            return []
        payload = self._query(
            class_name="HifyDocumentChunk",
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            model_name=model_name,
            top_k=top_k,
            fields="chunk_id document_id chunk_index content token_count",
        )
        rows = _weaviate_rows(payload, "HifyDocumentChunk")
        return [
            SimilarChunk(
                chunk=ChunkRecord(
                    id=int(_row_value(row, "chunk_id", "chunkId", "id") or 0),
                    document_id=int(_row_value(row, "document_id", "documentId") or 0),
                    chunk_index=int(_row_value(row, "chunk_index", "chunkIndex") or 0),
                    content=str(row.get("content") or ""),
                    token_count=int(_row_value(row, "token_count", "tokenCount") or 0),
                ),
                score=_weaviate_score(row),
            )
            for row in rows
        ]

    def search_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarFaq]:
        if not self.base_url:
            return []
        payload = self._query(
            class_name="HifyKnowledgeFaq",
            knowledge_base_id=knowledge_base_id,
            query_embedding=query_embedding,
            model_name=model_name,
            top_k=top_k,
            fields="faq_id question answer",
        )
        rows = _weaviate_rows(payload, "HifyKnowledgeFaq")
        return [
            SimilarFaq(
                faq={
                    "id": int(_row_value(row, "faq_id", "faqId", "id") or 0),
                    "question": str(row.get("question") or ""),
                    "answer": str(row.get("answer") or ""),
                    "metadata": row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
                },
                score=_weaviate_score(row),
            )
            for row in rows
        ]

    def replace_document_embeddings(
        self,
        knowledge_base_id: int,
        chunks: Sequence[ChunkRecord],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        if len(chunks) != len(embeddings):
            raise ValueError("chunks and embeddings length mismatch")
        if not self.base_url or not chunks:
            return []
        document_ids = sorted({chunk.document_id for chunk in chunks})
        for document_id in document_ids:
            self._delete_where(
                class_name="HifyDocumentChunk",
                where=_and_where(
                    [
                        _equal_int("knowledge_base_id", knowledge_base_id),
                        _equal_text("embedding_model", model_name),
                        _equal_int("document_id", document_id),
                    ]
                ),
            )
        rows: list[dict[str, Any]] = []
        for chunk, embedding in zip(chunks, embeddings, strict=True):
            self._put_object(
                class_name="HifyDocumentChunk",
                object_id=_object_id("HifyDocumentChunk", model_name, chunk.id),
                properties={
                    "knowledge_base_id": int(knowledge_base_id),
                    "embedding_model": model_name,
                    "chunk_id": int(chunk.id),
                    "document_id": int(chunk.document_id),
                    "chunk_index": int(chunk.chunk_index),
                    "content": chunk.content,
                    "token_count": int(chunk.token_count),
                },
                vector=embedding,
            )
            rows.append({"chunk_id": chunk.id, "embedding_model": model_name})
        return rows

    def replace_faq_embeddings(
        self,
        knowledge_base_id: int,
        faqs: Sequence[dict[str, Any]],
        embeddings: Sequence[Sequence[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, Any]]:
        if len(faqs) != len(embeddings):
            raise ValueError("faqs and embeddings length mismatch")
        if not self.base_url or not faqs:
            return []
        faq_ids = sorted({int(faq["id"]) for faq in faqs})
        for faq_id in faq_ids:
            self._delete_where(
                class_name="HifyKnowledgeFaq",
                where=_and_where(
                    [
                        _equal_int("knowledge_base_id", knowledge_base_id),
                        _equal_text("embedding_model", model_name),
                        _equal_int("faq_id", faq_id),
                    ]
                ),
            )
        rows: list[dict[str, Any]] = []
        for faq, embedding in zip(faqs, embeddings, strict=True):
            faq_id = int(faq["id"])
            self._put_object(
                class_name="HifyKnowledgeFaq",
                object_id=_object_id("HifyKnowledgeFaq", model_name, faq_id),
                properties={
                    "knowledge_base_id": int(knowledge_base_id),
                    "embedding_model": model_name,
                    "faq_id": faq_id,
                    "question": str(faq.get("question") or ""),
                    "answer": str(faq.get("answer") or ""),
                },
                vector=embedding,
            )
            rows.append({"faq_id": faq_id, "embedding_model": model_name})
        return rows

    def _query(
        self,
        *,
        class_name: str,
        knowledge_base_id: int,
        query_embedding: Sequence[float],
        model_name: str,
        top_k: int,
        fields: str,
    ) -> dict[str, Any]:
        if top_k <= 0:
            return {}
        query = f"""
        {{
          Get {{
            {class_name}(
              limit: {int(top_k)}
              nearVector: {{ vector: {_vector_literal(query_embedding)} }}
              where: {{
                operator: And
                operands: [
                  {{ path: [\"knowledge_base_id\"], operator: Equal, valueInt: {int(knowledge_base_id)} }}
                  {{ path: [\"embedding_model\"], operator: Equal, valueText: \"{_escape_graphql(model_name)}\" }}
                ]
              }}
            ) {{
              {fields}
              _additional {{ certainty distance }}
            }}
          }}
        }}
        """
        response = self._client.post(f"{self.base_url}/v1/graphql", json={"query": query})
        response.raise_for_status()
        payload = response.json()
        return payload if isinstance(payload, dict) else {}

    def _delete_where(self, *, class_name: str, where: dict[str, Any]) -> None:
        response = self._client.request(
            "DELETE",
            f"{self.base_url}/v1/batch/objects",
            json={
                "match": {"class": class_name, "where": where},
                "output": "minimal",
                "dryRun": False,
            },
        )
        response.raise_for_status()

    def _put_object(
        self,
        *,
        class_name: str,
        object_id: str,
        properties: dict[str, Any],
        vector: Sequence[float],
    ) -> None:
        response = self._client.post(
            f"{self.base_url}/v1/objects",
            json={
                "class": class_name,
                "id": object_id,
                "properties": properties,
                "vector": [float(value) for value in vector],
            },
        )
        response.raise_for_status()


def _weaviate_rows(payload: dict[str, Any], class_name: str) -> list[dict[str, Any]]:
    data = payload.get("data") if isinstance(payload, dict) else None
    get_payload = data.get("Get") if isinstance(data, dict) else None
    rows = get_payload.get(class_name) if isinstance(get_payload, dict) else None
    return [row for row in rows if isinstance(row, dict)] if isinstance(rows, list) else []


def _weaviate_score(row: dict[str, Any]) -> float:
    additional = row.get("_additional") if isinstance(row.get("_additional"), dict) else {}
    if "certainty" in additional:
        return float(additional.get("certainty") or 0.0)
    if "distance" in additional:
        return max(0.0, 1.0 - float(additional.get("distance") or 1.0))
    return 0.0


def _row_value(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row:
            return row[key]
    return None


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ", ".join(str(float(value)) for value in values) + "]"


def _escape_graphql(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _object_id(class_name: str, model_name: str, item_id: int) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"hify:{class_name}:{model_name}:{int(item_id)}"))


def _equal_int(path: str, value: int) -> dict[str, Any]:
    return {"path": [path], "operator": "Equal", "valueInt": int(value)}


def _equal_text(path: str, value: str) -> dict[str, Any]:
    return {"path": [path], "operator": "Equal", "valueText": value}


def _and_where(operands: Sequence[dict[str, Any]]) -> dict[str, Any]:
    return {"operator": "And", "operands": list(operands)}
