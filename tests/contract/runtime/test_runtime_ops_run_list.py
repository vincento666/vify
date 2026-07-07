from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from time import time_ns

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.core.db_write import insert_and_get_id
from app.main import app


class RuntimeOpsRunListApiTest(unittest.TestCase):
    def test_runtime_run_list_filters_by_owner_state_time_and_tenant(self) -> None:
        now = datetime.now()
        tenant_a = f"tenant-a-{time_ns()}"
        tenant_b = f"tenant-b-{time_ns()}"
        workflow_id = _insert_workflow("Workflow Alpha", "WORKFLOW")
        chatflow_id = _insert_workflow("Chatflow Beta", "CHATFLOW")
        workflow_run_id = _insert_run(workflow_id, "RUNNING", created_at=now - timedelta(minutes=20))
        queued_chatflow_run_id = _insert_run(chatflow_id, "RUNNING", created_at=now - timedelta(minutes=10))
        succeeded_run_id = _insert_run(workflow_id, "SUCCEEDED", created_at=now - timedelta(days=3))
        _insert_job(workflow_run_id, "WORKFLOW", workflow_id, "RUNNING", tenant_id=tenant_a)
        _insert_job(queued_chatflow_run_id, "CHATFLOW", chatflow_id, "QUEUED", tenant_id=tenant_b)
        _insert_job(succeeded_run_id, "WORKFLOW", workflow_id, "COMPLETED", tenant_id=tenant_a)

        with TestClient(app) as client:
            workflow_response = client.get(
                "/api/v1/runtime-runs",
                params={
                    "ownerType": "WORKFLOW",
                    "state": "running",
                    "tenantId": tenant_a,
                    "createdFrom": (now - timedelta(hours=1)).isoformat(),
                    "createdTo": (now + timedelta(minutes=1)).isoformat(),
                    "page": 1,
                    "pageSize": 20,
                },
            )
            chatflow_response = client.get(
                "/api/v1/runtime-runs",
                params={"ownerType": "CHATFLOW", "state": "queued", "tenantId": tenant_b},
            )

        self.assertEqual(workflow_response.status_code, 200, workflow_response.text)
        workflow_data = workflow_response.json()["data"]
        self.assertEqual(workflow_data["total"], 1)
        self.assertEqual(workflow_data["list"][0]["runId"], workflow_run_id)
        self.assertEqual(workflow_data["list"][0]["ownerType"], "WORKFLOW")
        self.assertEqual(workflow_data["list"][0]["ownerId"], workflow_id)
        self.assertEqual(workflow_data["list"][0]["ownerName"], "Workflow Alpha")
        self.assertEqual(workflow_data["list"][0]["state"], "running")
        self.assertEqual(workflow_data["list"][0]["status"], "RUNNING")
        self.assertEqual(workflow_data["list"][0]["tenantId"], tenant_a)
        self.assertEqual(workflow_data["list"][0]["queueState"], "running")

        self.assertEqual(chatflow_response.status_code, 200, chatflow_response.text)
        chatflow_data = chatflow_response.json()["data"]
        self.assertEqual(chatflow_data["total"], 1)
        self.assertEqual(chatflow_data["list"][0]["runId"], queued_chatflow_run_id)
        self.assertEqual(chatflow_data["list"][0]["ownerType"], "CHATFLOW")
        self.assertEqual(chatflow_data["list"][0]["state"], "queued")
        self.assertEqual(chatflow_data["list"][0]["tenantId"], tenant_b)


def _insert_workflow(name: str, flow_type: str) -> int:
    now = datetime.now()
    table = Base.metadata.tables["workflow"]
    with get_session_factory()() as session:
        workflow_id = insert_and_get_id(
            session,
            table,
            {
                "name": name,
                "description": "",
                "flow_type": flow_type,
                "status": "PUBLISHED",
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
        return int(workflow_id)


def _insert_run(workflow_id: int, status: str, *, created_at: datetime) -> int:
    table = Base.metadata.tables["workflow_run"]
    with get_session_factory()() as session:
        run_id = insert_and_get_id(
            session,
            table,
            {
                "workflow_id": workflow_id,
                "status": status,
                "input": {"_runtimeV2": {"ownerType": "WORKFLOW"}},
                "output": {},
                "error": "",
                "elapsed_ms": 0,
                "finished_at": created_at if status in {"SUCCEEDED", "FAILED", "CANCELLED"} else None,
                "deleted": False,
                "created_at": created_at,
                "updated_at": created_at,
            },
        )
        session.commit()
        return int(run_id)


def _insert_job(run_id: int, owner_type: str, owner_id: int, status: str, *, tenant_id: str) -> int:
    now = datetime.now()
    table = Base.metadata.tables["runtime_jobs"]
    with get_session_factory()() as session:
        job_id = insert_and_get_id(
            session,
            table,
            {
                "run_id": run_id,
                "owner_type": owner_type,
                "owner_id": owner_id,
                "job_type": "runtime_v2_completion",
                "status": status,
                "priority": 100,
                "attempt_count": 0,
                "max_attempts": 3,
                "lease_owner": "worker-a" if status == "RUNNING" else "",
                "lease_token": "",
                "lease_expires_at": None,
                "last_heartbeat_at": now if status == "RUNNING" else None,
                "available_at": now,
                "started_at": now if status == "RUNNING" else None,
                "finished_at": now if status == "COMPLETED" else None,
                "last_error": "",
                "payload": {"tenantId": tenant_id, "providerKeys": []},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
        return int(job_id)
