import unittest
from datetime import datetime
from typing import Any

from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.workflow.domain.engine import WorkflowExecutionEngine
from tests.support.local_api import LocalApiServer


class WorkflowSixNodeMatrixTest(unittest.TestCase):
    def test_full_existing_six_node_chain_uses_branching_variables_and_outputs(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)
        repository = _SixNodeRepositoryStub(server.url)
        knowledge_facade = _KnowledgeFacadeStub()
        llm_completer = _LlmCompleterStub()
        engine = WorkflowExecutionEngine(
            repository,
            knowledge_facade=knowledge_facade,
            llm_completer=llm_completer,
        )

        result = engine.run(8112, {"route": "kb", "question": "refund"})

        self.assertEqual(result.status, "SUCCEEDED")
        self.assertEqual(
            result.output,
            {"final": "Final API_REAL: POST /text/LLM_MATRIX_OK"},
        )
        self.assertEqual(repository.executed_node_types, ["START", "CONDITION", "KNOWLEDGE", "LLM", "API_CALL", "END"])
        self.assertEqual(knowledge_facade.requests, [(42, "Lookup refund", 2)])
        self.assertIn("Refund policy matrix context.", llm_completer.prompts[0])

    def test_selected_node_matrix_runs_each_existing_node_type_without_downstream(self) -> None:
        server = LocalApiServer()
        server.start()
        self.addCleanup(server.stop)
        repository = _SixNodeRepositoryStub(server.url)
        knowledge_facade = _KnowledgeFacadeStub()
        llm_completer = _LlmCompleterStub()
        engine = WorkflowExecutionEngine(
            repository,
            knowledge_facade=knowledge_facade,
            llm_completer=llm_completer,
        )

        cases = [
            ("start", {"route": "kb", "question": "refund"}, {"route": "kb", "question": "refund"}),
            ("router", {"route": "kb"}, {"route": "kb"}),
            ("kb", {"question": "refund"}, {"answer": "Refund policy matrix context."}),
            (
                "llm",
                {"kb": {"answer": "KB fixture"}},
                {
                    "answer": "LLM_MATRIX_OK",
                    "events": [
                        {"type": "llm_delta", "nodeKey": "llm", "content": "LLM_MATRIX_OK"},
                        {"type": "message_done", "nodeKey": "llm", "content": "LLM_MATRIX_OK"},
                    ],
                },
            ),
            (
                "api",
                {"llm": {"answer": "LLM_MATRIX_OK"}},
                {"response": "API_REAL: POST /text/LLM_MATRIX_OK"},
            ),
            ("end", {"api": {"response": "API fixture"}}, {"final": "Final API fixture"}),
        ]

        for node_key, input_data, expected_output in cases:
            with self.subTest(node_key=node_key):
                result = engine.run_node(8112, node_key, input_data)
                self.assertEqual(result.status, "SUCCEEDED")
                self.assertEqual(result.output, expected_output)

        self.assertEqual(knowledge_facade.requests, [(42, "Lookup refund", 2)])


class _SixNodeRepositoryStub:
    def __init__(self, api_base_url: str) -> None:
        now = datetime.now()
        self.api_base_url = api_base_url
        self.workflow = {
            "id": 8112,
            "name": "Six node matrix",
            "description": "",
            "flow_type": "WORKFLOW",
            "status": "DRAFT",
            "created_at": now,
            "updated_at": now,
        }
        self.executed_node_types: list[str] = []

    def get(self, workflow_id: int) -> dict[str, Any] | None:
        return self.workflow if workflow_id == 8112 else None

    def list_nodes(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"node_key": "start", "type": "START", "name": "Start", "config": {}},
            {
                "node_key": "router",
                "type": "CONDITION",
                "name": "Router",
                "config": {"expression": "{{start.route}}", "outputVariable": "route"},
            },
            {
                "node_key": "kb",
                "type": "KNOWLEDGE",
                "name": "Knowledge",
                "config": {
                    "query": "Lookup {{start.question}}",
                    "knowledgeBaseId": 42,
                    "topK": 2,
                    "outputVariable": "answer",
                },
            },
            {
                "node_key": "llm",
                "type": "LLM",
                "name": "LLM",
                "config": {
                    "prompt": "Summarize matrix context: {{kb.answer}}",
                    "outputVariable": "answer",
                },
            },
            {
                "node_key": "api",
                "type": "API_CALL",
                "name": "API",
                "config": {
                    "method": "POST",
                    "endpoint": f"{self.api_base_url}/text/{{{{llm.answer}}}}",
                    "outputVariable": "response",
                },
            },
            {
                "node_key": "end",
                "type": "END",
                "name": "End",
                "config": {
                    "outputVariable": "final",
                    "output": "Final {{api.response}}",
                },
            },
        ]

    def list_edges(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"source_node_key": "start", "target_node_key": "router", "condition_expr": None},
            {"source_node_key": "router", "target_node_key": "end", "condition_expr": None},
            {"source_node_key": "router", "target_node_key": "kb", "condition_expr": "kb"},
            {"source_node_key": "kb", "target_node_key": "llm", "condition_expr": None},
            {"source_node_key": "llm", "target_node_key": "api", "condition_expr": None},
            {"source_node_key": "api", "target_node_key": "end", "condition_expr": None},
        ]

    def create_run(self, _workflow_id: int, _input_data: dict[str, Any]) -> int:
        return 88112

    def create_node_run(
        self,
        _run_id: int,
        _node_key: str,
        node_type: str,
        inputs: dict[str, object] | None = None,
    ) -> int:
        del inputs
        self.executed_node_types.append(node_type)
        return len(self.executed_node_types)

    def finish_node_run(
        self,
        _node_run_id: int,
        _status: str,
        outputs: dict[str, Any],
        error: str | None = None,
        elapsed_ms: int = 0,
    ) -> None:
        return None

    def finish_run(
        self,
        _run_id: int,
        _status: str,
        output: dict[str, Any],
        error: str | None = None,
    ) -> None:
        return None


class _KnowledgeFacadeStub:
    def __init__(self) -> None:
        self.requests: list[tuple[int, str, int]] = []

    def search_chunks(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int = 3,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> list[KnowledgeSearchResult]:
        del retrieval_mode, score_threshold, rerank
        self.requests.append((knowledge_base_id, query, top_k))
        return [
            KnowledgeSearchResult(
                chunk_id=index + 1,
                document_id=2,
                chunk_index=index,
                content="Refund policy matrix context.",
                token_count=4,
                score=0.99 - index * 0.01,
            )
            for index in range(top_k)
        ]


class _LlmCompleterStub:
    def __init__(self) -> None:
        self.prompts: list[str] = []

    def complete_prompt(self, prompt: str, _options: dict[str, object] | None = None) -> str:
        self.prompts.append(prompt)
        return "LLM_MATRIX_OK"


if __name__ == "__main__":
    unittest.main()
