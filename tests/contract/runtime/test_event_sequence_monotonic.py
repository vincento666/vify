from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import threading

from app.core.schema import register_baseline_tables
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from tests.support.mysql import Mysql8TestDatabase


def test_event_sequence_is_strictly_monotonic_when_frontier_nodes_finish_concurrently() -> None:
    worker_count = 12
    run_id = 2156001
    chatflow_id = 2156
    session_id = "runtime-v2-sequence-2156"

    with Mysql8TestDatabase("runtime_event_sequence") as database:
        database.create_all(register=register_baseline_tables)
        barrier = threading.Barrier(worker_count)

        def append_event(index: int) -> int:
            barrier.wait(timeout=5)
            with database.session() as session:
                repository = ChatflowStateRepository(session)
                event = repository.append_event(
                    session_id=session_id,
                    chatflow_id=chatflow_id,
                    run_id=run_id,
                    event_type="workflow_node_completed",
                    node_key=f"node_{index}",
                    payload={"nodeIndex": index},
                )
                return int(event["sequence"])

        with ThreadPoolExecutor(max_workers=worker_count) as executor:
            sequences = list(executor.map(append_event, range(worker_count)))

        with database.session() as session:
            stored = ChatflowStateRepository(session).list_events(chatflow_id, run_id)

    assert sorted(sequences) == list(range(1, worker_count + 1))
    assert [int(event["sequence"]) for event in stored] == list(range(1, worker_count + 1))
