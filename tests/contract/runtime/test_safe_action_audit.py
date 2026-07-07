from __future__ import annotations

import unittest
from time import time_ns

from fastapi.testclient import TestClient

from app.core.database import get_session_factory
from app.main import app
from app.modules.audit.infra.repository import AuditRepository
from app.modules.workflow.infra.runtime_job_repository import RuntimeJobRepository
from app.modules.workflow.web.router import get_chatflow_runtime_v2_service


class RuntimeOpsSafeActionAuditTest(unittest.TestCase):
    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_chatflow_runtime_v2_service, None)

    def test_cancel_resume_retry_and_reopen_actions_write_audit_rows(self) -> None:
        app.dependency_overrides[get_chatflow_runtime_v2_service] = lambda: _FakeRuntimeService()
        actor_id = f"operator-2207-{time_ns()}"
        cancel_run_id = 2_207_300 + (time_ns() % 100_000)
        resume_run_id = cancel_run_id + 1
        retry_job = _failed_job(2_207_100 + (time_ns() % 100_000), error="retryable failure")
        reopen_job = _resolved_job(2_207_200 + (time_ns() % 100_000), error="operator resolved")
        headers = {"X-Hify-Actor-Id": actor_id, "X-Hify-Tenant-Id": "tenant-safe-actions"}

        with TestClient(app) as client:
            cancel = client.post(
                f"/api/v1/runtime-runs/{cancel_run_id}/cancel",
                json={"reason": "operator cancel", "deadlineMs": 500},
                headers=headers,
            )
            resume = client.post(
                f"/api/v1/runtime-runs/{resume_run_id}/resume",
                json={"resumeData": {"answer": "continue"}, "idempotencyKey": "resume-702"},
                headers=headers,
            )
            retry = client.post(f"/api/v1/runtime-jobs/{retry_job['id']}/retry", headers=headers)
            reopen = client.post(
                f"/api/v1/runtime-jobs/{reopen_job['id']}/reopen",
                json={"reason": "operator reopened"},
                headers=headers,
            )

        self.assertEqual(cancel.status_code, 200, cancel.text)
        self.assertEqual(resume.status_code, 200, resume.text)
        self.assertEqual(retry.status_code, 200, retry.text)
        self.assertEqual(reopen.status_code, 200, reopen.text)

        audit_by_action = _audit_by_action(
            {
                "RUNTIME_OPS_CANCEL_RUN": str(cancel_run_id),
                "RUNTIME_OPS_RESUME_RUN": str(resume_run_id),
                "RUNTIME_OPS_RETRY_JOB": str(retry_job["id"]),
                "RUNTIME_OPS_REOPEN_DLQ": str(reopen_job["id"]),
            },
            actor_id=actor_id,
        )
        self.assertEqual(audit_by_action["RUNTIME_OPS_CANCEL_RUN"]["actor"], actor_id)
        self.assertEqual(audit_by_action["RUNTIME_OPS_CANCEL_RUN"]["resource_id"], str(cancel_run_id))
        self.assertEqual(audit_by_action["RUNTIME_OPS_RESUME_RUN"]["resource_id"], str(resume_run_id))
        self.assertEqual(audit_by_action["RUNTIME_OPS_RETRY_JOB"]["resource_id"], str(retry_job["id"]))
        self.assertEqual(audit_by_action["RUNTIME_OPS_REOPEN_DLQ"]["resource_id"], str(reopen_job["id"]))
        self.assertEqual(audit_by_action["RUNTIME_OPS_REOPEN_DLQ"]["metadata"]["reason"], "operator reopened")


class _FakeRuntimeService:
    def cancel_run(self, run_id: int, *, reason: str, deadline_ms: int) -> dict[str, object]:
        return {"runId": run_id, "status": "CANCELLED", "reason": reason, "deadlineMs": deadline_ms}

    def resume_run(
        self,
        run_id: int,
        resume_data: dict[str, object],
        idempotency_key: str | None = None,
    ) -> dict[str, object]:
        return {"runId": run_id, "status": "SUCCEEDED", "resumeData": resume_data, "idempotencyKey": idempotency_key}


def _failed_job(run_id: int, *, error: str) -> dict[str, object]:
    with get_session_factory()() as session:
        repository = RuntimeJobRepository(session)
        created = repository.enqueue(run_id=run_id, owner_type="WORKFLOW", owner_id=run_id, max_attempts=1)
        claimed = repository.claim(int(created["id"]), worker_id=f"worker-{run_id}", lease_seconds=30)
        assert claimed is not None
        return repository.fail(
            int(created["id"]),
            worker_id=f"worker-{run_id}",
            lease_token=str(claimed["lease_token"]),
            error=error,
        )


def _resolved_job(run_id: int, *, error: str) -> dict[str, object]:
    failed = _failed_job(run_id, error=error)
    with get_session_factory()() as session:
        return RuntimeJobRepository(session).mark_dlq_resolved(int(failed["id"]), reason=error)


def _audit_by_action(expected: dict[str, str], *, actor_id: str) -> dict[str, dict[str, object]]:
    rows: dict[str, dict[str, object]] = {}
    with get_session_factory()() as session:
        repository = AuditRepository(session)
        for action, resource_id in expected.items():
            page, _total = repository.list_page(action=action, page_size=50)
            matched = [row for row in page if str(row["resource_id"]) == resource_id and row["actor"] == actor_id]
            assert len(matched) == 1, f"Expected one audit row for {action}/{resource_id}, got {len(matched)}"
            rows[action] = matched[0]
    return rows
