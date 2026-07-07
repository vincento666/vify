import time
import unittest

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.workflow.infra.repository import WorkflowRepository


class RuntimeWaitingNodeSetContractTest(unittest.TestCase):
    def test_runtime_result_exposes_waiting_nodes_as_a_set(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(client)
            run_id = _seed_interrupted_run_with_two_waiting_nodes(int(chatflow["id"]))

            status_payload = client.get(f"/api/v1/runtime-runs/{run_id}").json()["data"]
            result_payload = client.get(f"/api/v1/runtime-runs/{run_id}/result").json()["data"]

        self.assertEqual(status_payload["status"], "INTERRUPTED")
        self.assertEqual(status_payload["waitingNodeKeys"], ["collect_1", "handoff_1"])
        self.assertEqual(result_payload["waitingNodeKeys"], ["collect_1", "handoff_1"])
        self.assertEqual(
            [
                (node["nodeKey"], node["nodeType"], node["status"])
                for node in result_payload["waitingNodes"]
            ],
            [
                ("collect_1", "INFORMATION_COLLECTION", "WAITING"),
                ("handoff_1", "TRANSFER_TO_HUMAN", "WAITING"),
            ],
        )


def _seed_interrupted_run_with_two_waiting_nodes(chatflow_id: int) -> int:
    with get_session_factory()() as session:
        repository = WorkflowRepository(session)
        run_id = repository.create_run(chatflow_id, {"sys.query": "multi wait"})
        collect_run_id = repository.create_node_run(run_id, "collect_1", "INFORMATION_COLLECTION")
        repository.finish_node_run(collect_run_id, "WAITING", {})
        handoff_run_id = repository.create_node_run(run_id, "handoff_1", "TRANSFER_TO_HUMAN")
        repository.finish_node_run(handoff_run_id, "WAITING", {})
        repository.finish_run(run_id, "INTERRUPTED", {"interrupt": {"nodeKey": "collect_1"}})
        return run_id


def _create_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Runtime Waiting Node Set {time.time_ns()}",
            "description": "contract fixture for waiting node set projection",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "collect_1",
                    "type": "INFORMATION_COLLECTION",
                    "name": "Collect",
                    "config": {
                        "fields": [{"name": "phone", "type": "string", "required": True}],
                    },
                },
                {
                    "nodeKey": "handoff_1",
                    "type": "TRANSFER_TO_HUMAN",
                    "name": "Handoff",
                    "config": {"queue": "vip"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "collect_1", "condition": None},
                {"sourceNodeKey": "start", "targetNodeKey": "handoff_1", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]
