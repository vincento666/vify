import unittest
from datetime import datetime
from typing import Any

from app.core.errors import BizError
from app.modules.knowledge.api.facade import KnowledgeSearchResult
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.web.schemas import WorkflowRunRequest


class WorkflowServiceKnowledgeConditionTest(unittest.TestCase):
    def test_condition_branch_can_execute_real_knowledge_facade(self) -> None:
        knowledge_facade = _KnowledgeFacadeStub()
        service = WorkflowService(
            _KnowledgeConditionRepositoryStub(),
            flow_type="WORKFLOW",
            knowledge_facade=knowledge_facade,
        )

        result = service.execute(321, WorkflowRunRequest(input={"route": "kb", "question": "refund"}))

        self.assertEqual(result["status"], "SUCCEEDED")
        self.assertEqual(result["output"]["answer"], "Refunds are available within 7 days.")
        self.assertNotIn("Knowledge mock:", result["output"]["answer"])
        self.assertEqual(knowledge_facade.requests, [(42, "Lookup refund", 1)])

    def test_knowledge_node_without_facade_is_rejected_instead_of_mocked(self) -> None:
        service = WorkflowService(_KnowledgeConditionRepositoryStub(), flow_type="WORKFLOW")

        with self.assertRaises(BizError) as error:
            service.execute(321, WorkflowRunRequest(input={"route": "kb", "question": "refund"}))

        self.assertIn("Workflow knowledge facade is not configured", str(error.exception))


class _KnowledgeConditionRepositoryStub:
    def __init__(self) -> None:
        now = datetime.now()
        self.workflow = {
            "id": 321,
            "name": "Knowledge condition workflow",
            "description": "",
            "flow_type": "WORKFLOW",
            "status": "DRAFT",
            "created_at": now,
            "updated_at": now,
        }

    def get(self, workflow_id: int, _flow_type: str | None = None) -> dict[str, Any] | None:
        return self.workflow if workflow_id == 321 else None

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
                    "outputVariable": "answer",
                },
            },
            {
                "node_key": "fallback",
                "type": "END",
                "name": "Fallback",
                "config": {"outputVariable": "answer", "output": "fallback"},
            },
            {"node_key": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
        ]

    def list_edges(self, _workflow_id: int) -> list[dict[str, Any]]:
        return [
            {"source_node_key": "start", "target_node_key": "router", "condition_expr": None},
            {"source_node_key": "router", "target_node_key": "fallback", "condition_expr": None},
            {"source_node_key": "router", "target_node_key": "kb", "condition_expr": "kb"},
            {"source_node_key": "kb", "target_node_key": "end", "condition_expr": None},
        ]

    def create_run(self, _workflow_id: int, _input_data: dict[str, Any]) -> int:
        return 9901

    def create_node_run(self, _run_id: int, _node_key: str, _node_type: str) -> int:
        return 88

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
    ) -> list[KnowledgeSearchResult]:
        self.requests.append((knowledge_base_id, query, top_k))
        return [
            KnowledgeSearchResult(
                chunk_id=1,
                document_id=2,
                chunk_index=0,
                content="Refunds are available within 7 days.",
                token_count=7,
                score=0.98,
            )
        ]
