import importlib
import unittest

import sqlalchemy as sa

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
        unique_constraints = {
            constraint.name: tuple(column.name for column in constraint.columns)
            for constraint in table.constraints
            if isinstance(constraint, sa.UniqueConstraint)
        }

        self.assertTrue(required_columns.issubset(set(table.c.keys())))
        self.assertEqual(
            unique_constraints["idx_runtime_jobs_owner_run_type"],
            ("owner_type", "run_id", "job_type"),
        )

    def test_runtime_job_repository_supports_claim_heartbeat_terminal_and_cancel_paths(self) -> None:
        module = importlib.import_module("app.modules.runtime.infra.runtime_job_repository")
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
