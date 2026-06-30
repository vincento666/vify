from contextlib import contextmanager
import unittest
from collections.abc import Iterator, Mapping
from typing import Any

from sqlalchemy.orm import Session

from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import (
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionResult,
    SopExecutionStatus,
)
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class AdapterRequestUsesAggregatorTest(unittest.TestCase):
    def test_adapter_request_business_refs_do_not_come_from_task_business_refs(self) -> None:
        with _session() as db_session:
            repository = RuntimeLabRepository(db_session)
            aggregator = _FixedAggregator(
                {
                    "order_no": "AGG-ORDER",
                    "phone": "13900000000",
                    "passenger_count": "团队",
                    "poison": "from_aggregator",
                }
            )
            service = RuntimeLabService(repository, aggregator=aggregator)
            runtime_session = repository.create_session()
            session_id = int(runtime_session["id"])
            task = repository.create_task(
                session_id,
                sop_id="refund_ticket",
                business_refs={"poison": "from_task", "passenger_count": "from_task"},
            )
            checkpoint_row = repository.create_checkpoint(
                session_id,
                int(task["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                pending_prompt="",
                collected={},
                scoped_variables={},
            )

            request = service._adapter_request(  # noqa: SLF001
                session_id,
                "refund_ticket",
                message="退刚才订的票",
                task=task,
                checkpoint_row=checkpoint_row,
                collected=aggregator.collect(session_id),
            )

            self.assertNotEqual(request.business_refs, task["business_refs"])
            self.assertNotIn("poison", request.business_refs)
            self.assertNotIn("passenger_count", request.business_refs)
            self.assertEqual(request.collected["order_no"], "AGG-ORDER")
            self.assertEqual(request.collected["phone"], "13900000000")
            self.assertNotIn("passenger_count", request.collected)
            assert request.checkpoint is not None
            self.assertNotIn("passenger_count", request.checkpoint.collected)

    def test_suspend_task_uses_aggregator_not_task_business_refs(self) -> None:
        with _session() as db_session:
            repository = RuntimeLabRepository(db_session)
            adapter = _RecordingSuspendAdapter()
            aggregator = _FixedAggregator(
                {
                    "order_no": "AGG-SUSPEND",
                    "phone": "13900000001",
                    "passenger_count": "团队",
                    "poison": "from_aggregator",
                }
            )
            service = RuntimeLabService(repository, adapter=adapter, aggregator=aggregator)
            runtime_session = repository.create_session()
            session_id = int(runtime_session["id"])
            task = repository.create_task(
                session_id,
                sop_id="refund_ticket",
                business_refs={"order_no": "TASK-POISON", "poison": "from_task"},
            )
            repository.create_checkpoint(
                session_id,
                int(task["id"]),
                sop_id="refund_ticket",
                current_step="collect_order_no",
                pending_prompt="",
                collected={},
                scoped_variables={},
            )

            service._suspend_task(session_id, task)  # noqa: SLF001

            self.assertEqual(aggregator.collect_calls, [session_id])
            self.assertEqual(len(adapter.suspend_requests), 1)
            request = adapter.suspend_requests[0]
            self.assertNotIn("TASK-POISON", request.collected.values())
            self.assertNotIn("from_task", request.collected.values())
            # Spec 213.3.5e bans business_refs DB writes, so the poisoned task
            # value is never persisted and can never reach the adapter request.
            self.assertNotIn("TASK-POISON", request.business_refs.values())
            self.assertNotIn("from_task", request.business_refs.values())


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_adapter_request_aggregator", register=register_runtime_lab_tables) as session:
        yield session


class _FixedAggregator:
    def __init__(self, context: Mapping[str, Any]) -> None:
        self._context = dict(context)
        self.recorded_contexts: list[dict[str, Any]] = []
        self.collect_calls: list[int] = []

    def collect(self, session_id: int) -> dict[str, Any]:
        self.collect_calls.append(session_id)
        return dict(self._context)

    def record_turn_context(self, _session_id: int, context: Mapping[str, Any]) -> None:
        self.recorded_contexts.append(dict(context))


class _RecordingSuspendAdapter:
    def __init__(self) -> None:
        self.suspend_requests: list[SopExecutionRequest] = []

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return _result(request)

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return _result(request)

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        self.suspend_requests.append(request)
        return _checkpoint(request, dict(request.collected))

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        return _result(request)

    def is_interruptible(self, _sop_id: str, _step_id: str) -> bool:
        return True


def _result(request: SopExecutionRequest) -> SopExecutionResult:
    collected = dict(request.collected)
    return SopExecutionResult(
        status=SopExecutionStatus.WAITING,
        current_step="collect_order_no",
        reply="请补充信息。",
        pending_prompt="请补充信息。",
        checkpoint=_checkpoint(request, collected),
        collected=collected,
        business_refs=collected,
        events=[],
    )


def _checkpoint(request: SopExecutionRequest, collected: dict[str, Any]) -> SopCheckpoint:
    return SopCheckpoint(
        sop_runtime_id=f"test:{request.sop_id}:{request.runtime_task_id or 'new'}",
        current_node_id="collect_order_no",
        current_step="collect_order_no",
        pending_prompt="",
        collected=collected,
        scoped_variables={f"conversation.{key}": value for key, value in collected.items()},
        version=1,
    )
