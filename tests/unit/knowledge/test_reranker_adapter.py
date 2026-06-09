import unittest

import httpx

from app.modules.knowledge.domain.retrieval import (
    HttpReranker,
    RerankCandidate,
    RrfReranker,
    create_reranker,
)


class RerankerAdapterTest(unittest.TestCase):
    def test_rrf_reranker_exposes_adapter_contract(self) -> None:
        reranker = RrfReranker()

        ranked = reranker.rerank_rankings(
            query="refund",
            rankings=[
                ["doc-semantic", "doc-both"],
                ["doc-both", "doc-keyword"],
            ],
            top_k=2,
        )

        self.assertEqual(["doc-both", "doc-semantic"], [entry.item for entry in ranked])

    def test_http_reranker_posts_query_and_candidates(self) -> None:
        seen: dict[str, object] = {}

        def handler(request: httpx.Request) -> httpx.Response:
            seen["url"] = str(request.url)
            seen["authorization"] = request.headers.get("authorization")
            seen["payload"] = request.read().decode("utf-8")
            return httpx.Response(
                200,
                json={"results": [{"id": "b", "score": 0.99}, {"id": "a", "score": 0.44}]},
            )

        reranker = HttpReranker(
            endpoint="http://rerank.local/rerank",
            api_key="rk-test",
            http_client=httpx.Client(transport=httpx.MockTransport(handler)),
        )

        ranked = reranker.rerank(
            "refund",
            [
                RerankCandidate(id="a", text="A", score=0.1),
                RerankCandidate(id="b", text="B", score=0.2),
            ],
            top_k=2,
        )

        self.assertEqual("http://rerank.local/rerank", seen["url"])
        self.assertEqual("Bearer rk-test", seen["authorization"])
        self.assertIn("refund", str(seen["payload"]))
        self.assertEqual(["b", "a"], [candidate.id for candidate in ranked])
        self.assertEqual([0.99, 0.44], [candidate.score for candidate in ranked])

    def test_factory_selects_http_reranker_when_configured(self) -> None:
        reranker = create_reranker(
            {
                "provider": "http",
                "endpoint": "http://rerank.local/rerank",
                "api_key": "rk-test",
            }
        )

        self.assertIsInstance(reranker, HttpReranker)


if __name__ == "__main__":
    unittest.main()
