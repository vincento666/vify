import unittest

import httpx

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.chunks import ChunkRecord
from app.modules.knowledge.domain.vector_search import SimilarChunk, SimilarFaq
from app.modules.knowledge.domain.vector_store import (
    RepositoryVectorStore,
    WeaviateVectorStore,
    create_vector_store,
)


class _EmbeddingProvider:
    model_name = "test-embedding"

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [[1.0, 0.0] for _ in texts]


class _Repository:
    def __init__(self) -> None:
        self.chunk_calls = 0
        self.faq_calls = 0
        self.replaced_chunks: tuple[object, ...] | None = None
        self.replaced_faqs: tuple[object, ...] | None = None

    def search_similar_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        self.chunk_calls += 1
        return [
            SimilarChunk(
                chunk=ChunkRecord(1, 2, 0, "semantic chunk", 2),
                score=0.9,
            )
        ]

    def search_similar_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarFaq]:
        self.faq_calls += 1
        return [SimilarFaq(faq={"id": 3, "question": "Refund?", "answer": "Use form."}, score=0.8)]

    def replace_document_embeddings(
        self,
        chunks: list[ChunkRecord],
        embeddings: list[list[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, object]]:
        self.replaced_chunks = (chunks, embeddings, model_name, dimensions)
        return [{"chunk_id": chunk.id} for chunk in chunks]

    def replace_faq_embeddings(
        self,
        faqs: list[dict[str, object]],
        embeddings: list[list[float]],
        model_name: str,
        dimensions: int,
    ) -> list[dict[str, object]]:
        self.replaced_faqs = (faqs, embeddings, model_name, dimensions)
        return [{"faq_id": faq["id"]} for faq in faqs]


class _NoDirectVectorRepository:
    def get(self, knowledge_base_id: int) -> dict[str, int]:
        return {"id": knowledge_base_id}

    def search_similar_chunks(self, *args: object, **kwargs: object) -> list[SimilarChunk]:
        raise AssertionError("facade must call vector store adapter")

    def list_done_documents(self, knowledge_base_id: int) -> list[dict[str, int]]:
        return []

    def list_enabled_faqs(self, knowledge_base_id: int) -> list[dict[str, object]]:
        return []


class _VectorStore:
    def search_chunks(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarChunk]:
        return [SimilarChunk(chunk=ChunkRecord(9, 8, 0, "adapter chunk", 2), score=0.77)]

    def search_faqs(
        self,
        knowledge_base_id: int,
        query_embedding: list[float],
        model_name: str,
        top_k: int,
    ) -> list[SimilarFaq]:
        return []


class VectorStoreAdapterTest(unittest.TestCase):
    def test_repository_vector_store_delegates_to_repository(self) -> None:
        repository = _Repository()
        store = RepositoryVectorStore(repository)

        self.assertEqual("semantic chunk", store.search_chunks(1, [1.0, 0.0], "test", 3)[0].chunk.content)
        self.assertEqual("Refund?", store.search_faqs(1, [1.0, 0.0], "test", 3)[0].faq["question"])
        self.assertEqual(1, repository.chunk_calls)
        self.assertEqual(1, repository.faq_calls)

    def test_repository_vector_store_delegates_embedding_writes(self) -> None:
        repository = _Repository()
        store = RepositoryVectorStore(repository)
        chunks = [ChunkRecord(1, 2, 0, "semantic chunk", 2)]
        faqs = [{"id": 3, "question": "Refund?", "answer": "Use form."}]

        self.assertEqual(
            [{"chunk_id": 1}],
            store.replace_document_embeddings(9, chunks, [[0.1, 0.9]], "test-model", 2),
        )
        self.assertEqual(
            [{"faq_id": 3}],
            store.replace_faq_embeddings(9, faqs, [[0.3, 0.7]], "test-model", 2),
        )

        self.assertEqual((chunks, [[0.1, 0.9]], "test-model", 2), repository.replaced_chunks)
        self.assertEqual((faqs, [[0.3, 0.7]], "test-model", 2), repository.replaced_faqs)

    def test_unconfigured_weaviate_store_is_safe_empty_adapter(self) -> None:
        store = WeaviateVectorStore(base_url="")

        self.assertEqual([], store.search_chunks(1, [1.0], "test", 3))
        self.assertEqual([], store.search_faqs(1, [1.0], "test", 3))

    def test_factory_selects_weaviate_store_when_configured(self) -> None:
        store = create_vector_store(
            _Repository(),
            {"provider": "weaviate", "base_url": "http://localhost:8080"},
        )

        self.assertIsInstance(store, WeaviateVectorStore)
        self.assertEqual("http://localhost:8080", store.base_url)

    def test_weaviate_store_queries_document_chunk_class(self) -> None:
        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            payload = request.read().decode("utf-8")
            seen["payload"] = payload
            return httpx.Response(
                200,
                json={
                    "data": {
                        "Get": {
                            "HifyDocumentChunk": [
                                {
                                    "chunk_id": 42,
                                    "document_id": 7,
                                    "chunk_index": 1,
                                    "content": "weaviate semantic chunk",
                                    "token_count": 3,
                                    "_additional": {"certainty": 0.91},
                                }
                            ]
                        }
                    }
                },
            )

        store = WeaviateVectorStore(
            base_url="http://weaviate.local",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        results = store.search_chunks(5, [0.1, 0.2], "test-model", 2)

        self.assertEqual("http://weaviate.local/v1/graphql", seen["url"])
        self.assertIn("HifyDocumentChunk", str(seen["payload"]))
        self.assertIn("knowledge_base_id", str(seen["payload"]))
        self.assertEqual("weaviate semantic chunk", results[0].chunk.content)
        self.assertEqual(0.91, results[0].score)

    def test_weaviate_store_queries_faq_class(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(
                200,
                json={
                    "data": {
                        "Get": {
                            "HifyKnowledgeFaq": [
                                {
                                    "faq_id": 9,
                                    "question": "How refund?",
                                    "answer": "Use the refund form.",
                                    "metadata": {"source": "weaviate"},
                                    "_additional": {"distance": 0.2},
                                }
                            ]
                        }
                    }
                },
            )

        store = WeaviateVectorStore(
            base_url="http://weaviate.local",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        results = store.search_faqs(5, [0.1, 0.2], "test-model", 2)

        self.assertEqual(9, results[0].faq["id"])
        self.assertEqual("How refund?", results[0].faq["question"])
        self.assertEqual(0.8, results[0].score)

    def test_weaviate_store_replaces_document_embeddings(self) -> None:
        requests: list[tuple[str, str]] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, str(request.url)))
            return httpx.Response(200, json={})

        store = WeaviateVectorStore(
            base_url="http://weaviate.local",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        chunks = [ChunkRecord(11, 22, 0, "indexed document chunk", 3)]

        rows = store.replace_document_embeddings(44, chunks, [[0.1, 0.2]], "test-model", 2)

        self.assertEqual([{"chunk_id": 11, "embedding_model": "test-model"}], rows)
        self.assertIn(("GET", "http://weaviate.local/v1/schema/HifyDocumentChunk"), requests)
        self.assertIn(("DELETE", "http://weaviate.local/v1/batch/objects"), requests)
        self.assertEqual("POST", requests[-1][0])
        self.assertEqual("http://weaviate.local/v1/objects", requests[-1][1])

    def test_weaviate_store_creates_document_chunk_schema_before_upsert(self) -> None:
        requests: list[tuple[str, str]] = []
        payloads: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            requests.append((request.method, str(request.url)))
            payloads.append(request.read().decode("utf-8"))
            if request.method == "GET" and str(request.url).endswith("/v1/schema/HifyDocumentChunk"):
                return httpx.Response(404, json={"error": "missing class"})
            return httpx.Response(200, json={})

        store = WeaviateVectorStore(
            base_url="http://weaviate.local",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        store.replace_document_embeddings(
            44,
            [ChunkRecord(11, 22, 0, "indexed document chunk", 3)],
            [[0.1, 0.2]],
            "test-model",
            2,
        )

        self.assertIn(("GET", "http://weaviate.local/v1/schema/HifyDocumentChunk"), requests)
        self.assertIn(("POST", "http://weaviate.local/v1/schema"), requests)
        self.assertTrue(any('"class":"HifyDocumentChunk"' in payload for payload in payloads))

    def test_weaviate_store_replaces_faq_embeddings(self) -> None:
        payloads: list[str] = []

        def handler(request: httpx.Request) -> httpx.Response:
            payloads.append(request.read().decode("utf-8"))
            return httpx.Response(200, json={})

        store = WeaviateVectorStore(
            base_url="http://weaviate.local",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )
        faqs = [{"id": 33, "knowledge_base_id": 44, "question": "Refund?", "answer": "Use form."}]

        rows = store.replace_faq_embeddings(44, faqs, [[0.3, 0.7]], "test-model", 2)

        self.assertEqual([{"faq_id": 33, "embedding_model": "test-model"}], rows)
        self.assertIn("HifyKnowledgeFaq", payloads[-1])
        self.assertIn("Refund?", payloads[-1])

    def test_facade_uses_vector_store_adapter_for_semantic_recall(self) -> None:
        facade = KnowledgeFacade.__new__(KnowledgeFacade)
        facade._repository = _NoDirectVectorRepository()  # type: ignore[attr-defined]
        facade._embedding_provider = _EmbeddingProvider()  # type: ignore[attr-defined]
        facade._vector_store = _VectorStore()  # type: ignore[attr-defined]

        results = facade.search_context(1, "refund", top_k=1, retrieval_mode="semantic")

        self.assertEqual("adapter chunk", results[0].content)


if __name__ == "__main__":
    unittest.main()
