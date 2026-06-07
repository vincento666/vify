import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
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
        checkpoint = SopCheckpoint(
            sop_runtime_id=f"failing:{request.sop_id}",
            current_node_id="",
            current_step="",
            pending_prompt="",
            collected={},
            scoped_variables={},
            version=1,
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


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_sop_adapter_contract.db"
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
