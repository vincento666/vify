"""Spec 213.3.5g — SOP Router stops persisting Chatflow execution mirrors."""

import unittest

import sqlalchemy as sa

from app.modules.runtime_lab.domain import payload
from app.modules.runtime_lab.domain import service as service_module
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables, runtime_lab_tables


class RuntimeLabSopStateBoundaryTest(unittest.TestCase):
    def test_runtime_lab_schema_drops_checkpoint_table_and_banned_task_columns(self) -> None:
        metadata = sa.MetaData()

        register_runtime_lab_tables(metadata)

        self.assertNotIn("runtime_lab_checkpoint", metadata.tables)
        task_columns = set(metadata.tables["runtime_lab_task"].c.keys())
        self.assertNotIn("current_step", task_columns)
        self.assertNotIn("business_refs", task_columns)

    def test_runtime_lab_tables_omits_checkpoint_table(self) -> None:
        table_names = {table.name for table in runtime_lab_tables()}

        self.assertNotIn("runtime_lab_checkpoint", table_names)

    def test_repository_removes_checkpoint_accessors(self) -> None:
        self.assertFalse(hasattr(RuntimeLabRepository, "create_checkpoint"))
        self.assertFalse(hasattr(RuntimeLabRepository, "get_checkpoint"))
        self.assertFalse(hasattr(RuntimeLabRepository, "get_latest_checkpoint"))

    def test_service_removes_legacy_state_delegates(self) -> None:
        self.assertFalse(hasattr(RuntimeLabService, "_session_business_context"))
        self.assertFalse(hasattr(service_module, "_sop_checkpoint_from_row"))

    def test_task_payload_omits_chatflow_mirror_fields(self) -> None:
        row = {
            "id": 1,
            "session_id": 2,
            "sop_id": "refund_ticket",
            "status": "RUNNING",
            "current_step": "confirm",
            "checkpoint_id": 3,
            "parent_task_id": None,
            "resume_summary": "",
            "business_refs": {"order_no": "T1"},
            "chatflow_id": 42,
            "chatflow_session_id": 77,
            "chatflow_run_id": 9001,
            "chatflow_event_id": 12345,
            "chatflow_checkpoint_id": 9999,
            "runtime_version": "v2",
            "suspended_at": None,
            "completed_at": None,
            "created_at": None,
            "updated_at": None,
        }

        formatted = payload.format_task(row)

        self.assertNotIn("currentStep", formatted)
        self.assertNotIn("businessRefs", formatted)
        self.assertIn("chatflowSession", formatted)


if __name__ == "__main__":
    unittest.main()
