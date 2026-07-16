from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.core.schema import register_baseline_tables
from app.modules.runtime_lab.web.router import _runtime_lab_child_event_reader
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from tests.support.mysql import mysql8_session


def test_runtime_lab_child_reader_tails_only_events_after_cursor() -> None:
    with _session() as session:
        workflows = WorkflowRepository(session)
        chatflow = workflows.create(
            {"name": "RuntimeLab stream reader", "description": "test fixture", "flow_type": "CHATFLOW"},
            nodes=[],
            edges=[],
        )
        chatflow_id = int(chatflow["id"])
        run_id = workflows.create_run(chatflow_id, {})
        events = ChatflowStateRepository(session)
        events.append_event(
            session_id="runtime-lab-stream",
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_started",
            payload={"runId": run_id},
        )
        read_child_events = _runtime_lab_child_event_reader(session, None)

        initial = read_child_events(run_id, 0, 100)

        events.append_event(
            session_id="runtime-lab-stream",
            chatflow_id=chatflow_id,
            run_id=run_id,
            event_type="workflow_run_interrupted",
            node_key="collect_phone",
            payload={"output": {"prompt": "请输入手机号"}},
        )
        tailed = read_child_events(run_id, 1, 100)

    assert [(event["sequence"], event["type"]) for event in initial] == [(1, "workflow_run_started")]
    assert [(event["sequence"], event["type"]) for event in tailed] == [(2, "workflow_run_interrupted")]


def test_waiting_checkpoint_is_claimed_once_and_released_after_worker_failure() -> None:
    with _session() as session:
        workflows = WorkflowRepository(session)
        chatflow = workflows.create(
            {"name": "RuntimeLab checkpoint claim", "description": "test fixture", "flow_type": "CHATFLOW"},
            nodes=[],
            edges=[],
        )
        chatflow_id = int(chatflow["id"])
        run_id = workflows.create_run(chatflow_id, {})
        state = ChatflowStateRepository(session)
        checkpoint = state.create_checkpoint(
            session_id="runtime-lab-claim",
            chatflow_id=chatflow_id,
            run_id=run_id,
            pending_node_key="collect_phone",
            execution_context={"input": {}},
            node_outputs={},
            variable_scopes={},
            resume_schema={"type": "QUESTION"},
        )

        claimed = state.claim_waiting_checkpoint(chatflow_id, run_id, int(checkpoint["id"]))
        duplicate = state.claim_waiting_checkpoint(chatflow_id, run_id, int(checkpoint["id"]))
        state.release_checkpoint_claim(int(checkpoint["id"]))
        retried = state.claim_waiting_checkpoint(chatflow_id, run_id, int(checkpoint["id"]))

    assert claimed is not None
    assert claimed["status"] == "resuming"
    assert duplicate is None
    assert retried is not None
    assert retried["status"] == "resuming"


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_sop_live_stream", register=register_baseline_tables) as session:
        yield session
