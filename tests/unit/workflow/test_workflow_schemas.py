import unittest

try:
    from app.modules.workflow.web.schemas import WorkflowCreateRequest
except ImportError:
    WorkflowCreateRequest = None  # type: ignore[assignment]


class WorkflowSchemaTest(unittest.TestCase):
    def test_create_request_parses_graph_with_camel_case_keys(self) -> None:
        self.assertIsNotNone(WorkflowCreateRequest)

        request = WorkflowCreateRequest(
            name="Support Flow",
            description="route support tickets",
            nodes=[
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {"nodeKey": "end", "type": "END", "name": "End", "config": {"outputVariable": "answer"}},
            ],
            edges=[{"sourceNodeKey": "start", "targetNodeKey": "end", "condition": None}],
        )

        self.assertEqual(request.nodes[0].node_key, "start")
        self.assertEqual(request.edges[0].source_node_key, "start")

    def test_missing_edges_defaults_to_empty_list(self) -> None:
        self.assertIsNotNone(WorkflowCreateRequest)

        request = WorkflowCreateRequest(
            name="Single",
            nodes=[{"nodeKey": "start", "type": "START", "name": "Start", "config": {}}],
        )

        self.assertEqual(request.edges, [])


if __name__ == "__main__":
    unittest.main()
