from contextlib import contextmanager
import unittest
from collections.abc import Iterator
from unittest.mock import patch

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
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


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_v2_events", register=register_baseline_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
