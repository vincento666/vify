import unittest
from unittest.mock import patch

import httpx

from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.knowledge.domain.service import KnowledgeBaseService
from app.modules.knowledge.domain.embeddings import (
    FakeEmbeddingProvider,
    LocalSentenceTransformerEmbeddingProvider,
    OpenRouterEmbeddingProvider,
    create_embedding_provider,
)
from app.modules.knowledge.domain.vector_store import WeaviateVectorStore


class EmbeddingProviderAdapterTest(unittest.TestCase):
    def test_openrouter_embedding_provider_uses_embeddings_api(self) -> None:
        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers.get("authorization")
            seen["payload"] = request.read().decode("utf-8")
            return httpx.Response(
                200,
                json={
                    "model": "sentence-transformers/all-minilm-l6-v2",
                    "data": [{"embedding": [0.1, 0.2, 0.3]}],
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        provider = OpenRouterEmbeddingProvider(
            api_key="sk-test",
            model_name="sentence-transformers/all-minilm-l6-v2",
            http_client=client,
        )

        self.assertEqual([[0.1, 0.2, 0.3]], provider.embed(["refund policy"]))
        self.assertEqual("https://openrouter.ai/api/v1/embeddings", seen["url"])
        self.assertEqual("Bearer sk-test", seen["authorization"])
        self.assertIn("sentence-transformers/all-minilm-l6-v2", str(seen["payload"]))

    def test_factory_keeps_fake_provider_as_safe_default(self) -> None:
        provider = create_embedding_provider({})

        self.assertIsInstance(provider, FakeEmbeddingProvider)

    def test_local_sentence_transformer_provider_uses_injected_model(self) -> None:
        class _Model:
            def encode(self, texts: list[str], normalize_embeddings: bool = True) -> list[list[float]]:
                self.seen = (texts, normalize_embeddings)
                return [[0.4, 0.6]]

        model = _Model()
        provider = LocalSentenceTransformerEmbeddingProvider(
            model_name="sentence-transformers/all-MiniLM-L6-v2",
            model_loader=lambda _name: model,
        )

        self.assertEqual([[0.4, 0.6]], provider.embed(["refund policy"]))
        self.assertEqual((["refund policy"], True), model.seen)
        self.assertEqual("sentence-transformers/all-MiniLM-L6-v2", provider.model_name)

    def test_factory_can_select_local_hf_provider(self) -> None:
        provider = create_embedding_provider(
            {
                "provider": "local-hf",
                "model": "sentence-transformers/all-MiniLM-L6-v2",
                "model_loader": lambda _name: type(
                    "_Model",
                    (),
                    {"encode": lambda self, texts, normalize_embeddings=True: [[0.2, 0.8] for _ in texts]},
                )(),
            }
        )

        self.assertIsInstance(provider, LocalSentenceTransformerEmbeddingProvider)

    def test_factory_uses_local_hf_model_env(self) -> None:
        with patch.dict(
            "os.environ",
            {"HIFY_LOCAL_EMBEDDING_MODEL": "sentence-transformers/paraphrase-minilm-l6-v2"},
            clear=True,
        ):
            provider = create_embedding_provider(
                {
                    "provider": "local-hf",
                    "model_loader": lambda _name: type(
                        "_Model",
                        (),
                        {"encode": lambda self, texts, normalize_embeddings=True: [[0.1, 0.9] for _ in texts]},
                    )(),
                }
            )

        self.assertEqual("sentence-transformers/paraphrase-minilm-l6-v2", provider.model_name)

    def test_knowledge_service_uses_embedding_provider_factory(self) -> None:
        with patch.dict(
            "os.environ",
            {
                "HIFY_EMBEDDING_PROVIDER": "openrouter",
                "OPENROUTER_API_KEY": "sk-test",
                "HIFY_OPENROUTER_EMBEDDING_MODEL": "nvidia/llama-nemotron-embed-vl-1b-v2:free",
            },
        ):
            service = KnowledgeBaseService(object())  # type: ignore[arg-type]

        self.assertIsInstance(service._embedding_provider, OpenRouterEmbeddingProvider)  # noqa: SLF001

    def test_knowledge_facade_uses_embedding_and_vector_store_factories(self) -> None:
        class _Repository:
            pass

        with (
            patch("app.modules.knowledge.api.facade.KnowledgeBaseRepository", lambda _session: _Repository()),
            patch.dict(
                "os.environ",
                {
                    "HIFY_EMBEDDING_PROVIDER": "openrouter",
                    "OPENROUTER_API_KEY": "sk-test",
                    "HIFY_OPENROUTER_EMBEDDING_MODEL": "nvidia/llama-nemotron-embed-vl-1b-v2:free",
                    "HIFY_VECTOR_STORE": "weaviate",
                    "HIFY_WEAVIATE_URL": "http://127.0.0.1:8080",
                },
            ),
        ):
            facade = KnowledgeFacade(object())  # type: ignore[arg-type]

        self.assertIsInstance(facade._embedding_provider, OpenRouterEmbeddingProvider)  # noqa: SLF001
        self.assertIsInstance(facade._vector_store, WeaviateVectorStore)  # noqa: SLF001


if __name__ == "__main__":
    unittest.main()
