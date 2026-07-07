import unittest

import sqlalchemy as sa

from app.modules.runtime_lab.domain.aggregator import RuntimeLabBusinessContextAggregator
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class SopRouterLedgerSchemaTest(unittest.TestCase):
    def test_runtime_lab_ledger_tables_are_final_set(self) -> None:
        metadata = sa.MetaData()

        register_runtime_lab_tables(metadata)

        self.assertEqual(
            set(metadata.tables),
            {
                "runtime_lab_session",
                "runtime_lab_task",
                "runtime_lab_event",
                "runtime_lab_command",
            },
        )

    def test_task_ledger_columns_are_router_state_and_child_refs_only(self) -> None:
        metadata = sa.MetaData()

        register_runtime_lab_tables(metadata)

        self.assertEqual(
            set(metadata.tables["runtime_lab_task"].c.keys()),
            {
                "id",
                "session_id",
                "sop_id",
                "status",
                "parent_task_id",
                "resume_summary",
                "chatflow_id",
                "chatflow_session_id",
                "chatflow_run_id",
                "chatflow_event_id",
                "chatflow_checkpoint_id",
                "runtime_version",
                "suspended_at",
                "completed_at",
                "expires_at",
                "deleted",
                "created_at",
                "updated_at",
            },
        )

    def test_ledger_schema_has_no_chatflow_execution_mirror_columns(self) -> None:
        metadata = sa.MetaData()

        register_runtime_lab_tables(metadata)

        forbidden = {
            "current_step",
            "pending_prompt",
            "collected",
            "scoped_variables",
            "checkpoint_id",
            "business_refs",
            "node_events",
            "run_status",
            "runtime_status",
        }
        for table in metadata.tables.values():
            with self.subTest(table=table.name):
                self.assertTrue(forbidden.isdisjoint(table.c.keys()))

    def test_runtime_lab_code_has_no_current_step_side_channel(self) -> None:
        self.assertFalse(hasattr(RuntimeLabBusinessContextAggregator, "record_task_step"))
        self.assertFalse(hasattr(RuntimeLabBusinessContextAggregator, "task_current_step"))
        self.assertFalse(hasattr(RuntimeLabService, "_event_current_step"))

    def test_runtime_checkpoint_facts_do_not_fallback_to_router_ledger(self) -> None:
        service = RuntimeLabService(_EventLedgerOnlyRepository(), current_step_runtime=None)

        checkpoint = service._latest_checkpoint_with_overlay_step(  # noqa: SLF001
            {"id": 10, "session_id": 20, "current_step": "from_task_row", "chatflow_run_id": None}
        )

        self.assertIsNone(checkpoint)


class _EventLedgerOnlyRepository:
    def list_events(self, _session_id: int) -> list[dict[str, object]]:
        return [
            {
                "payload": {
                    "taskId": 10,
                    "currentStep": "from_runtime_lab_event",
                }
            }
        ]


if __name__ == "__main__":
    unittest.main()
