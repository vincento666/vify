"""Spec 213.3.1 contract — runtime_lab_task carries first-class chatflow ref columns.

`create_task` and `update_task_state` must accept and persist six new chatflow ref
columns so SOP Router can stop relying on the scoped_variables.__chatflow JSON
projection on `runtime_lab_checkpoint`.
"""

from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class RuntimeLabTaskRefColumnsTest(unittest.TestCase):
    def test_create_task_persists_chatflow_ref_columns(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()

            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                business_refs={"route": "BJ-SH"},
                chatflow_id=42,
                chatflow_session_id=77,
                chatflow_run_id=901,
                chatflow_event_id=12345,
                chatflow_checkpoint_id=99,
                runtime_version="v2",
            )

            self.assertEqual(task["chatflow_id"], 42)
            self.assertEqual(task["chatflow_session_id"], 77)
            self.assertEqual(task["chatflow_run_id"], 901)
            self.assertEqual(task["chatflow_event_id"], 12345)
            self.assertEqual(task["chatflow_checkpoint_id"], 99)
            self.assertEqual(task["runtime_version"], "v2")

            persisted = repository.get_task(int(task["id"]))
            assert persisted is not None
            self.assertEqual(persisted["chatflow_id"], 42)
            self.assertEqual(persisted["chatflow_session_id"], 77)
            self.assertEqual(persisted["chatflow_run_id"], 901)
            self.assertEqual(persisted["chatflow_event_id"], 12345)
            self.assertEqual(persisted["chatflow_checkpoint_id"], 99)
            self.assertEqual(persisted["runtime_version"], "v2")

    def test_update_task_state_can_set_ref_columns(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            runtime_session = repository.create_session()

            task = repository.create_task(
                int(runtime_session["id"]),
                sop_id="refund_ticket",
            )

            updated = repository.update_task_state(
                int(task["id"]),
                status="RUNNING",
                current_step="collect_order_no",
                chatflow_id=42,
                chatflow_session_id=77,
                chatflow_run_id=901,
                chatflow_event_id=12345,
                chatflow_checkpoint_id=99,
                runtime_version="v2",
            )

            self.assertEqual(updated["chatflow_id"], 42)
            self.assertEqual(updated["chatflow_session_id"], 77)
            self.assertEqual(updated["chatflow_run_id"], 901)
            self.assertEqual(updated["chatflow_event_id"], 12345)
            self.assertEqual(updated["chatflow_checkpoint_id"], 99)
            self.assertEqual(updated["runtime_version"], "v2")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_task_refs", register=register_runtime_lab_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
