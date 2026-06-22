import time
import unittest
from unittest.mock import patch

import sqlalchemy as sa
from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.main import app


class ChatflowRunGatewayApiTest(unittest.TestCase):
    def test_chatflow_runs_endpoint_is_runtime_v2_gateway_with_durable_job(self) -> None:
        with TestClient(app) as client, patch("app.modules.workflow.web.router.threading.Thread"):
            chatflow = _create_chatflow(client)
            version = client.post(f"/api/v1/chatflows/{chatflow['id']}/publish").json()["data"]
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs",
                json={
                    "input": {"sys.query": "gateway"},
                    "versionId": version["id"],
                    "idempotencyKey": f"chatflow-run-gateway-{time.time_ns()}",
                },
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        run_id = int(data["runId"])
        self.assertEqual(data["runtimeVersion"], 2)
        self.assertEqual(data["ownerType"], "CHATFLOW")
        self.assertEqual(data["ownerId"], chatflow["id"])
        self.assertEqual(data["chatflowId"], chatflow["id"])
        self.assertEqual(data["versionId"], version["id"])
        self.assertNotIn("output", data)
        self.assertEqual(data["status"], "RUNNING")
        self.assertEqual(data["statusRef"], f"/api/v1/runtime-runs/{run_id}")
        self.assertEqual(data["eventsRef"], f"/api/v1/runtime-runs/{run_id}/events")
        self.assertEqual(data["nodesRef"], f"/api/v1/runtime-runs/{run_id}/nodes")
        self.assertEqual(data["resultRef"], f"/api/v1/runtime-runs/{run_id}/result")
        self.assertEqual(
            data["runtimeRefs"],
            {
                "runId": run_id,
                "statusRef": data["statusRef"],
                "eventsRef": data["eventsRef"],
                "eventStreamRef": data["eventStreamRef"],
                "nodesRef": data["nodesRef"],
                "resultRef": data["resultRef"],
            },
        )
        job = _runtime_job_for_run(run_id)
        self.assertEqual(job["owner_type"], "CHATFLOW")
        self.assertEqual(job["owner_id"], chatflow["id"])
        self.assertEqual(job["job_type"], "runtime_v2_completion")
        self.assertEqual(job["status"], "QUEUED")

    def test_chatflow_runs_legacy_keeps_sync_compatibility(self) -> None:
        with TestClient(app) as client:
            chatflow = _create_chatflow(client)
            response = client.post(
                f"/api/v1/chatflows/{chatflow['id']}/runs-legacy",
                json={"input": {"sys.query": "legacy"}},
            )

        self.assertEqual(response.status_code, 200, response.text)
        data = response.json()["data"]
        self.assertEqual(data["status"], "SUCCEEDED")
        self.assertEqual(data["output"], {"final": "gateway message"})
        self.assertIn("debugUrl", data)


def _runtime_job_for_run(run_id: int) -> dict[str, object]:
    job_table = Base.metadata.tables["runtime_jobs"]
    with get_session_factory()() as session:
        row = (
            session.execute(
                sa.select(job_table)
                .where(job_table.c.run_id == run_id, job_table.c.deleted.is_(False))
                .order_by(job_table.c.id.desc())
            )
            .mappings()
            .first()
        )
    if row is None:
        raise AssertionError(f"No runtime job found for run {run_id}")
    return dict(row)


def _create_chatflow(client: TestClient) -> dict[str, object]:
    response = client.post(
        "/api/v1/chatflows",
        json={
            "name": f"Chatflow Run Gateway {time.time_ns()}",
            "description": "chatflow default run gateway contract fixture",
            "nodes": [
                {"nodeKey": "start", "type": "START", "name": "Start", "config": {}},
                {
                    "nodeKey": "message_1",
                    "type": "MESSAGE",
                    "name": "Message",
                    "config": {"content": "gateway message", "outputVariable": "content"},
                },
                {
                    "nodeKey": "end",
                    "type": "END",
                    "name": "End",
                    "config": {"outputVariable": "final", "output": "{{message_1.content}}"},
                },
            ],
            "edges": [
                {"sourceNodeKey": "start", "targetNodeKey": "message_1", "condition": None},
                {"sourceNodeKey": "message_1", "targetNodeKey": "end", "condition": None},
            ],
        },
    )
    assert response.status_code == 200, response.text
    return response.json()["data"]


if __name__ == "__main__":
    unittest.main()
