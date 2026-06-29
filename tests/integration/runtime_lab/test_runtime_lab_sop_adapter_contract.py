from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import (
    FakeSopRuntimeAdapter,
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionResult,
    SopExecutionStatus,
)
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabSopAdapterContractIntegrationTest(unittest.TestCase):
    def test_service_routes_start_continue_suspend_and_resume_through_adapter_port(self) -> None:
        with _session() as session:
            adapter = _RecordingSopRuntimeAdapter()
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository, adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要退票")
            service.handle_message(session_id, "我要开发票")
            service.handle_message(session_id, "INV-100")
            service.handle_message(session_id, "确认")
            turn = service.handle_message(session_id, "继续处理退票")

            self.assertEqual(adapter.calls["start_sop"], 2)
            self.assertGreaterEqual(adapter.calls["continue_sop"], 2)
            self.assertEqual(adapter.calls["suspend_sop"], 1)
            self.assertEqual(adapter.calls["resume_sop"], 1)
            self.assertEqual(turn.active_task["sop_id"], "refund_ticket")
            self.assertEqual([task["status"] for task in repository.list_tasks(session_id)], ["RUNNING", "COMPLETED"])

    def test_adapter_failure_is_normalized_without_creating_active_task(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository, adapter=_FailingStartAdapter())
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "我要退票")

            self.assertIn("SOP执行失败", turn.reply)
            self.assertIsNone(turn.active_task)
            self.assertEqual(repository.list_tasks(session_id), [])
            self.assertEqual(repository.list_events(session_id)[-1]["event_type"], "ERROR")

    def test_legacy_multi_level_router_path_handles_v2_start_failure_as_start_failed(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            adapter = ChatflowSopRuntimeAdapter(
                _NeverCalledWorkflowService(),
                sop_chatflow_ids={"refund_ticket": 1},
                runtime_v2_service=_FailingRuntimeV2Service(),
            )
            service = RuntimeLabService(repository, adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "我要退票")
            events = repository.list_events(session_id)

            self.assertIn("SOP执行失败", turn.reply)
            self.assertIsNone(turn.active_task)
            self.assertEqual(repository.list_tasks(session_id), [])
            self.assertEqual(events[-1]["event_type"], "ERROR")
            error = events[-1]["payload"]["error"]
            self.assertEqual(error["code"], "CHATFLOW_START_FAILED")
            self.assertEqual(error["runtimeCode"], "CHATFLOW_V2_START_FAILED")
            self.assertIn("runtime v2 queue unavailable", error["message"])


class _RecordingSopRuntimeAdapter(FakeSopRuntimeAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.calls = {
            "start_sop": 0,
            "continue_sop": 0,
            "suspend_sop": 0,
            "resume_sop": 0,
        }

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.calls["start_sop"] += 1
        return super().start_sop(request)

    def continue_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.calls["continue_sop"] += 1
        return super().continue_sop(request)

    def suspend_sop(self, request: SopExecutionRequest) -> SopCheckpoint:
        self.calls["suspend_sop"] += 1
        return super().suspend_sop(request)

    def resume_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.calls["resume_sop"] += 1
        return super().resume_sop(request)


class _FailingStartAdapter(FakeSopRuntimeAdapter):
    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        # Slice 213.3.5a: even the failure path emits a well-formed
        # __chatflow meta block so downstream consumers (which never run
        # in this branch but may in other matrix tests) have consistent shape.
        checkpoint = self._checkpoint(
            request,
            current_step="",
            pending_prompt="",
            collected={},
        )
        return SopExecutionResult(
            status=SopExecutionStatus.FAILED,
            current_step="",
            reply="",
            pending_prompt="",
            checkpoint=checkpoint,
            collected={},
            business_refs={},
            events=[{"type": "SOP_FAILED", "sopId": request.sop_id}],
            error={"code": "ADAPTER_FAILED", "message": "adapter down"},
        )


class _FailingRuntimeV2Service:
    def start_run(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        raise RuntimeError("runtime v2 queue unavailable")


class _NeverCalledWorkflowService:
    def execute(self, *_args: object, **_kwargs: object) -> dict[str, object]:
        raise AssertionError("legacy v1 workflow service should not run on v2 start failure")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_sop_adapter_contract", register=register_runtime_lab_tables) as session:
        yield session
