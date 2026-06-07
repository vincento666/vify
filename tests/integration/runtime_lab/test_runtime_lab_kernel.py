import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.errors import BizError, ErrorCode
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabKernelTest(unittest.TestCase):
    def test_command_replay_is_domain_level_and_preserves_invariants(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)
            runtime_session = service.create_session()

            first = service.handle_command(int(runtime_session["id"]), "我要退票", idempotency_key="kernel-start")
            second = service.handle_command(int(runtime_session["id"]), "我要退票", idempotency_key="kernel-start")

            tasks = repository.list_tasks(int(runtime_session["id"]))
            events = repository.list_events(int(runtime_session["id"]))

            self.assertFalse(first.replayed)
            self.assertTrue(second.replayed)
            self.assertEqual(second.payload, first.payload)
            self.assertEqual([task["status"] for task in tasks], ["RUNNING"])
            self.assertEqual([task["current_step"] for task in tasks], ["collect_order_no"])
            self.assertEqual([event["sequence"] for event in events], list(range(1, len(events) + 1)))
            self.assertEqual(
                [event["event_type"] for event in events],
                ["SESSION_CREATED", "USER_MESSAGE", "ROUTE_DECISION", "TASK_STARTED"],
            )

            with self.assertRaises(BizError) as mismatch:
                service.handle_command(int(runtime_session["id"]), "我要改签", idempotency_key="kernel-start")
            self.assertEqual(mismatch.exception.code, ErrorCode.BAD_REQUEST)

    def test_missing_session_command_rejected_before_events(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository)

            with self.assertRaises(BizError) as missing:
                service.handle_command(404_404, "我要退票", idempotency_key="missing")

            self.assertEqual(missing.exception.code, ErrorCode.NOT_FOUND)
            self.assertEqual(repository.list_events(404_404), [])


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_kernel.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_runtime_lab_tables()
    tables = [
        Base.metadata.tables["runtime_lab_session"],
        Base.metadata.tables["runtime_lab_task"],
        Base.metadata.tables["runtime_lab_checkpoint"],
        Base.metadata.tables["runtime_lab_event"],
        Base.metadata.tables["runtime_lab_command"],
    ]
    Base.metadata.create_all(bind=engine, tables=tables)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session
