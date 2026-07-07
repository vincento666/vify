from __future__ import annotations

import unittest
from datetime import datetime, timedelta
from time import time_ns

from fastapi.testclient import TestClient

from app.core.database import Base, get_session_factory
from app.core.db_write import insert_and_get_id
from app.main import app


class RuntimeOpsJobsApiTest(unittest.TestCase):
    def test_runtime_job_list_exposes_lease_heartbeat_attempt_and_retry_time(self) -> None:
        now = datetime.now()
        tenant_running = f"tenant-running-{time_ns()}"
        tenant_retry = f"tenant-retry-{time_ns()}"
        workflow_id = _insert_workflow("Workflow Jobs Alpha", "WORKFLOW")
        chatflow_id = _insert_workflow("Chatflow Jobs Beta", "CHATFLOW")
        running_run_id = _insert_run(workflow_id, "RUNNING", created_at=now - timedelta(minutes=15))
        retry_run_id = _insert_run(chatflow_id, "RUNNING", created_at=now - timedelta(minutes=10))
        running_job_id = _insert_job(
            running_run_id,
            "WORKFLOW",
            workflow_id,
            "RUNNING",
            tenant_id=tenant_running,
            lease_owner="worker-live",
            attempt_count=2,
            max_attempts=5,
            last_heartbeat_at=now - timedelta(seconds=30),
            lease_expires_at=now + timedelta(seconds=90),
        )
        retry_job_id = _insert_job(
            retry_run_id,
            "CHATFLOW",
            chatflow_id,
            "QUEUED",
            tenant_id=tenant_retry,
            attempt_count=1,
            max_attempts=3,
            available_at=now + timedelta(minutes=2),
            last_error="provider timeout",
        )

        with TestClient(app) as client:
            running_response = client.get(
                "/api/v1/runtime-jobs",
                params={"status": "RUNNING", "ownerType": "WORKFLOW", "tenantId": tenant_running},
            )
            retry_response = client.get(
                "/api/v1/runtime-jobs",
                params={"status": "QUEUED", "tenantId": tenant_retry},
            )

        self.assertEqual(running_response.status_code, 200, running_response.text)
        running_data = running_response.json()["data"]
        self.assertEqual(running_data["total"], 1)
        self.assertEqual(running_data["list"][0]["jobId"], running_job_id)
        self.assertEqual(running_data["list"][0]["runId"], running_run_id)
        self.assertEqual(running_data["list"][0]["ownerType"], "WORKFLOW")
        self.assertEqual(running_data["list"][0]["status"], "RUNNING")
        self.assertEqual(running_data["list"][0]["leaseOwner"], "worker-live")
        self.assertEqual(running_data["list"][0]["attemptCount"], 2)
        self.assertEqual(running_data["list"][0]["maxAttempts"], 5)
        self.assertEqual(running_data["list"][0]["tenantId"], tenant_running)
        self.assertTrue(running_data["list"][0]["lastHeartbeatAt"])
        self.assertTrue(running_data["list"][0]["leaseExpiresAt"])

        self.assertEqual(retry_response.status_code, 200, retry_response.text)
        retry_data = retry_response.json()["data"]
        self.assertEqual(retry_data["total"], 1)
        self.assertEqual(retry_data["list"][0]["jobId"], retry_job_id)
        self.assertEqual(retry_data["list"][0]["status"], "QUEUED")
        self.assertEqual(retry_data["list"][0]["nextRetryAt"], retry_data["list"][0]["availableAt"])
        self.assertEqual(retry_data["list"][0]["lastError"], "provider timeout")


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


def _insert_job(
    run_id: int,
    owner_type: str,
    owner_id: int,
    status: str,
    *,
    tenant_id: str,
    lease_owner: str = "",
    attempt_count: int = 0,
    max_attempts: int = 3,
    available_at: datetime | None = None,
    last_heartbeat_at: datetime | None = None,
    lease_expires_at: datetime | None = None,
    last_error: str = "",
) -> int:
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
                "attempt_count": attempt_count,
                "max_attempts": max_attempts,
                "lease_owner": lease_owner,
                "lease_token": "lease-token" if lease_owner else "",
                "lease_expires_at": lease_expires_at,
                "last_heartbeat_at": last_heartbeat_at,
                "available_at": available_at,
                "started_at": now if status == "RUNNING" else None,
                "finished_at": None,
                "last_error": last_error,
                "payload": {"tenantId": tenant_id, "providerKeys": []},
                "deleted": False,
                "created_at": now,
                "updated_at": now,
            },
        )
        session.commit()
        return int(job_id)
