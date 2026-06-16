import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.errors import BizError
from app.modules.customer_assistant.domain.models import TaskCommand, TaskCommandType
from app.modules.customer_assistant.domain.policy import UnsupportedTaskCommand
from app.modules.customer_assistant.domain.service import CustomerAssistantService
from app.modules.customer_assistant.infra.repository import CustomerAssistantRepository
from app.modules.customer_assistant.infra.schema import (
    customer_assistant_tables,
    register_customer_assistant_tables,
)


class CustomerAssistantEventTimingTest(unittest.TestCase):
    def test_recommendation_events_include_phase_timing_and_order(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(CustomerAssistantRepository(session))
            assistant_session = service.create_session()

            service.handle_turn(int(assistant_session["id"]), "我要退票", idempotency_key="timing")
            events = service.list_events(int(assistant_session["id"]))["list"]

        event_types = [event["type"] for event in events]
        started = events[event_types.index("recommendation_started")]
        completed = events[event_types.index("recommendation_completed")]
        self.assertLess(event_types.index("recommendation_started"), event_types.index("recommendation_completed"))
        self.assertLess(event_types.index("recommendation_completed"), event_types.index("run_completed"))
        self.assertIn("startedAt", started["payload"])
        self.assertIn("startedAt", completed["payload"])
        self.assertIn("completedAt", completed["payload"])
        self.assertGreaterEqual(completed["payload"]["elapsedMs"], 0)

    def test_controlled_runtime_exception_emits_run_failed_event(self) -> None:
        with _session() as session:
            service = CustomerAssistantService(
                CustomerAssistantRepository(session),
                core=_BadCore(),
            )
            assistant_session = service.create_session()

            with self.assertRaises(BizError):
                service.handle_turn(int(assistant_session["id"]), "boom", idempotency_key="failure")
            events = service.list_events(int(assistant_session["id"]))["list"]

        failure = [event for event in events if event["type"] == "run_failed"][0]
        self.assertEqual(failure["payload"]["error"], "unsupported test command")
        self.assertIn("completedAt", failure["payload"])


class _BadCore:
    def run(self, _context, action_handler, finalizer):
        _ = finalizer
        action_handler([TaskCommand(TaskCommandType.FINAL)])
        raise UnsupportedTaskCommand("unsupported test command")


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "customer_assistant_timing.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_customer_assistant_tables()
    Base.metadata.create_all(bind=engine, tables=customer_assistant_tables())
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


if __name__ == "__main__":
    unittest.main()
