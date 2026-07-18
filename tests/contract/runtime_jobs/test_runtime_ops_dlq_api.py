from __future__ import annotations

import unittest
from time import time_ns

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.runtime.infra.runtime_job_repository import RuntimeJobRepository


class RuntimeOpsDlqApiTest(unittest.TestCase):
    def test_dlq_list_retry_ignore_and_mark_resolved_actions(self) -> None:
        base_run_id = 2_206_000_000_000 + time_ns()
        tenant_id = f"tenant-dlq-api-{time_ns()}"
        retry_job = _failed_job(base_run_id, owner_id=42_001, error="provider timeout", tenant_id=tenant_id)
        ignore_job = _failed_job(base_run_id + 1, owner_id=42_002, error="tool failed", tenant_id=tenant_id)
        resolved_job = _failed_job(base_run_id + 2, owner_id=42_003, error="manual fix applied", tenant_id=tenant_id)

        with TestClient(app) as client:
            list_response = client.get("/api/v1/runtime-jobs/dlq", params={"tenantId": tenant_id})
            retry_response = client.post(f"/api/v1/runtime-jobs/{retry_job['id']}/retry")
            ignore_response = client.post(
                f"/api/v1/runtime-jobs/{ignore_job['id']}/ignore",
                json={"reason": "operator accepted loss"},
            )
            resolved_response = client.post(
                f"/api/v1/runtime-jobs/{resolved_job['id']}/mark-resolved",
                json={"reason": "operator verified upstream fix"},
            )
            empty_response = client.get("/api/v1/runtime-jobs/dlq", params={"tenantId": tenant_id})

        self.assertEqual(list_response.status_code, 200, list_response.text)
        self.assertEqual(list_response.json()["data"]["total"], 3)
        self.assertEqual(retry_response.status_code, 200, retry_response.text)
        self.assertEqual(retry_response.json()["data"]["jobId"], retry_job["id"])
        self.assertEqual(retry_response.json()["data"]["status"], "QUEUED")
        self.assertEqual(ignore_response.status_code, 200, ignore_response.text)
        self.assertEqual(ignore_response.json()["data"]["status"], "IGNORED")
        self.assertEqual(ignore_response.json()["data"]["lastError"], "operator accepted loss")
        self.assertEqual(resolved_response.status_code, 200, resolved_response.text)
        self.assertEqual(resolved_response.json()["data"]["status"], "RESOLVED")
        self.assertEqual(resolved_response.json()["data"]["lastError"], "operator verified upstream fix")
        self.assertEqual(empty_response.status_code, 200, empty_response.text)
        self.assertEqual(empty_response.json()["data"]["total"], 0)


def _failed_job(run_id: int, *, owner_id: int, error: str, tenant_id: str) -> dict[str, object]:
    with get_session_factory()() as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(
            run_id=run_id,
            owner_type="WORKFLOW",
            owner_id=owner_id,
            max_attempts=1,
            payload={"tenantId": tenant_id},
        )
        claimed = repository.claim(int(created["id"]), worker_id=f"worker-{run_id}", lease_seconds=30)
        assert claimed is not None
        return repository.fail(
            int(created["id"]),
            worker_id=f"worker-{run_id}",
            lease_token=str(claimed["lease_token"]),
            error=error,
        )
