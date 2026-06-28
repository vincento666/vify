"""Spec 213.3.3 step 2 — Aggregator parity with legacy ``_session_business_context``.

Asserts ``RuntimeLabBusinessContextAggregator.collect()`` returns the same dict
as the legacy ``RuntimeLabService._session_business_context`` for the scenarios
covered by ``test_runtime_lab_service.py:137-295``. Locks the migration
semantics before slice 213.3.3 step 3 switches call-sites.

The recording adapter does not set chatflow refs on tasks, so the aggregator
falls back to ``task.business_refs``. Because ``RuntimeLabService`` already
calls ``update_task_state(business_refs=result.collected)`` whenever a
checkpoint is created (see service.py:973-1011, 1038-1059), the
``business_refs`` field always reflects the latest checkpoint collected dict.
That makes the chatflow-less fallback equivalent to the legacy
``business_refs ∪ checkpoint.collected`` merge.
"""

import unittest
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy.orm import Session

from app.modules.runtime_lab.domain.aggregator import (
    RuntimeLabBusinessContextAggregator,
)
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


class AggregatorParityTest(unittest.TestCase):
    def test_parity_after_completed_booking_inherits_into_change_flight(self) -> None:
        with _session() as session:
            service, repository = _build(session)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "我想改签刚才的机票")

            self._assert_parity(service, repository, session_id)

    def test_parity_when_user_mentions_another_person(self) -> None:
        with _session() as session:
            service, repository = _build(session)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "我要给另一个人改签机票")

            self._assert_parity(service, repository, session_id)

    def test_parity_for_same_trip_reference(self) -> None:
        with _session() as session:
            service, repository = _build(session)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "我还想带宠物一起走，帮我办理宠物乘机")

            self._assert_parity(service, repository, session_id)

    def test_parity_active_continue_fills_referenced_slots(self) -> None:
        with _session() as session:
            service, repository = _build(session)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "我要团队订票")
            service.handle_message(session_id, "我要办理退票")
            service.handle_message(session_id, "退刚才订的那张票")

            self._assert_parity(service, repository, session_id)

    def test_parity_resume_does_not_default_fill(self) -> None:
        with _session() as session:
            service, repository = _build(session)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要办理退票")
            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "继续刚才")

            self._assert_parity(service, repository, session_id)

    def test_parity_resume_with_explicit_completed_reference(self) -> None:
        with _session() as session:
            service, repository = _build(session)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要办理退票")
            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "继续刚才，退刚订的那张票")

            self._assert_parity(service, repository, session_id)

    def _assert_parity(
        self,
        service: RuntimeLabService,
        repository: RuntimeLabRepository,
        session_id: int,
    ) -> None:
        legacy = service._session_business_context(session_id)  # noqa: SLF001
        aggregator = RuntimeLabBusinessContextAggregator(repository, None)
        new = aggregator.collect(session_id)
        self.assertEqual(
            new,
            legacy,
            msg=(
                "Aggregator parity mismatch — "
                f"legacy={legacy!r} aggregator={new!r}"
            ),
        )


def _build(session: Session) -> tuple[RuntimeLabService, RuntimeLabRepository]:
    repository = RuntimeLabRepository(session)
    adapter = _RecordingContextAdapter()
    service = RuntimeLabService(repository, adapter=adapter)
    return service, repository


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session(
        "runtime_lab_aggregator_parity", register=register_runtime_lab_tables
    ) as session:
        yield session


# Mirrors ``_RecordingContextAdapter`` from ``test_runtime_lab_service.py`` so
# this parity bench reuses the same scripted SOP outcomes (no chatflow refs).
class _RecordingContextAdapter:
    def __init__(self) -> None:
        self.start_requests: list[SopExecutionRequest] = []
        self.continue_requests: list[SopExecutionRequest] = []
        self.resume_requests: list[SopExecutionRequest] = []

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.start_requests.append(request)
        if request.sop_id == "flight_booking":
            collected = {
                "order_no": "CA1301-20231027-8899",
                "phone": "13800138000",
                "passenger_name": "张三",
            }
            return _adapter_result(request, "confirm", "是否确认预订？", collected, completed=False)
        if request.sop_id == "group_booking":
            collected = {"route": "上海到广州", "passenger_count": "团队"}
            return _adapter_result(request, "collect_order_no", "请补充信息。", collected, completed=False)
        return _adapter_result(request, "collect_order_no", "请补充信息。", request.collected, completed=False)

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.continue_requests.append(request)
        collected = dict(request.checkpoint.collected if request.checkpoint else request.collected)
        return _adapter_result(request, "completed", "", collected, completed=True)

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        if request.checkpoint is not None:
            return request.checkpoint
        return _adapter_checkpoint(request, "collect_order_no", "", request.collected)

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.resume_requests.append(request)
        collected = dict(request.checkpoint.collected if request.checkpoint else request.collected)
        return _adapter_result(request, "collect_order_no", "已恢复。", collected, completed=False)

    def is_interruptible(self, _sop_id: str, _step_id: str) -> bool:
        return True


def _adapter_result(
    request: SopExecutionRequest,
    current_step: str,
    prompt: str,
    collected: dict[str, object],
    *,
    completed: bool,
) -> SopExecutionResult:
    return SopExecutionResult(
        status=SopExecutionStatus.COMPLETED if completed else SopExecutionStatus.WAITING,
        current_step=current_step,
        reply=prompt or "已完成。",
        pending_prompt=prompt,
        checkpoint=_adapter_checkpoint(request, current_step, prompt, collected),
        collected=dict(collected),
        business_refs=dict(collected),
        events=[],
    )


def _adapter_checkpoint(
    request: SopExecutionRequest,
    current_step: str,
    prompt: str,
    collected: dict[str, object],
) -> SopCheckpoint:
    return SopCheckpoint(
        sop_runtime_id=f"test:{request.sop_id}:{current_step}",
        current_node_id=current_step,
        current_step=current_step,
        pending_prompt=prompt,
        collected=dict(collected),
        scoped_variables={f"conversation.{key}": value for key, value in collected.items()},
        version=1,
    )


if __name__ == "__main__":
    unittest.main()
