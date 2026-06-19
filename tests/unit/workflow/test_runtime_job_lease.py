import importlib
import unittest

from app.core.database import Base
from app.core.schema import register_baseline_tables


class RuntimeJobLeaseTest(unittest.TestCase):
    def test_runtime_jobs_table_exposes_lease_takeover_metadata(self) -> None:
        register_baseline_tables()

        self.assertIn("runtime_jobs", Base.metadata.tables)
        table = Base.metadata.tables["runtime_jobs"]
        required_columns = {
            "id",
            "run_id",
            "owner_type",
            "owner_id",
            "job_type",
            "status",
            "payload",
            "lease_owner",
            "lease_expires_at",
            "lease_token",
            "last_heartbeat_at",
            "available_at",
            "started_at",
            "finished_at",
            "last_error",
            "attempt_count",
            "max_attempts",
        }

        self.assertTrue(required_columns.issubset(set(table.c.keys())))

    def test_runtime_job_repository_supports_claim_heartbeat_terminal_and_cancel_paths(self) -> None:
        module = importlib.import_module("app.modules.workflow.infra.runtime_job_repository")
        repository_class = getattr(module, "RuntimeJobRepository")
        required_methods = {
            "enqueue",
            "claim_next",
            "claim",
            "heartbeat",
            "complete",
            "fail",
            "cancel_by_run",
        }

        self.assertTrue(required_methods.issubset(set(dir(repository_class))))


if __name__ == "__main__":
    unittest.main()
