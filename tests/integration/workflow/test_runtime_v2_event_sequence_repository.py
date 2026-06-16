import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository


class RuntimeV2EventSequenceRepositoryTest(unittest.TestCase):
    def test_append_event_recovers_from_stale_sequence_after_concurrent_writer(self) -> None:
        with _session() as session:
            repository = ChatflowStateRepository(session)
            repository.append_event(
                session_id="chatflow-v2-1",
                chatflow_id=10,
                run_id=20,
                event_type="workflow_run_started",
                payload={"message": "first"},
            )

            with patch.object(repository, "_next_sequence", side_effect=[1, 2]):
                second_event = repository.append_event(
                    session_id="chatflow-v2-1",
                    chatflow_id=10,
                    run_id=20,
                    event_type="workflow_node_started",
                    node_key="message_1",
                    payload={"message": "second"},
                )

            self.assertEqual(second_event["sequence"], 2)
            self.assertEqual([event["sequence"] for event in repository.list_events(10, 20)], [1, 2])


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_v2_events.db"
    engine = create_engine(f"sqlite:///{db_path}", future=True)
    register_baseline_tables()
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)
    session = factory()
    session.info["_tmp_dir"] = tmp_dir
    return session


if __name__ == "__main__":
    unittest.main()
