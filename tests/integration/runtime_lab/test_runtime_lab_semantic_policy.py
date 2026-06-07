import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabSemanticPolicyTest(unittest.TestCase):
    def test_no_active_strong_start_exits_before_classifier(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier()
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我要退票")

            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "refund_ticket")
            self.assertEqual(classifier.calls, 0)

    def test_no_active_conflict_calls_classifier_once_and_starts_selected_sop(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="invoice_apply")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我想退费并开发票")

            self.assertEqual(classifier.calls, 1)
            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "invoice_apply")

    def test_active_conflict_uses_classifier_before_sop_mutation(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="invoice_apply")
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository, classifier=classifier)
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            turn = service.handle_message(int(runtime_session["id"]), "我想退费并开发票")
            tasks = repository.list_tasks(int(runtime_session["id"]))

            self.assertEqual(classifier.calls, 1)
            self.assertEqual(turn.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(turn.active_task["sop_id"], "invoice_apply")
            self.assertEqual(tasks[0]["sop_id"], "refund_ticket")
            self.assertEqual(tasks[0]["business_refs"], {})

    def test_active_non_interruptible_classifier_switch_is_rejected(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="invoice_apply")
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository, classifier=classifier)
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            service.handle_message(int(runtime_session["id"]), "TK-100")
            turn = service.handle_message(int(runtime_session["id"]), "我需要报销凭证")
            tasks = repository.list_tasks(int(runtime_session["id"]))

            self.assertEqual(turn.route_decision.action, "REJECT_SWITCH_CONTINUE_ACTIVE")
            self.assertEqual([task["sop_id"] for task in tasks], ["refund_ticket"])
            self.assertEqual(tasks[0]["current_step"], "confirm")

    def test_suspended_task_semantic_candidate_can_resume(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(select_candidate_type="SUSPENDED_TASK_RESUME")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            service.handle_message(int(runtime_session["id"]), "我要开发票")
            service.handle_message(int(runtime_session["id"]), "INV-200")
            service.handle_message(int(runtime_session["id"]), "确认")
            turn = service.handle_message(int(runtime_session["id"]), "继续处理退票")

            self.assertEqual(turn.route_decision.action, "RESUME_TASK")
            self.assertEqual(turn.active_task["sop_id"], "refund_ticket")
            self.assertEqual(turn.suspended_tasks, [])


class _RecordingClassifier:
    def __init__(
        self,
        selected_target_id: str | None = None,
        select_candidate_type: str | None = None,
    ) -> None:
        self.calls = 0
        self.selected_target_id = selected_target_id
        self.select_candidate_type = select_candidate_type

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        self.calls += 1
        candidate = classifier_input.candidates[0]
        for item in classifier_input.candidates:
            if self.selected_target_id is not None and item.target_id == self.selected_target_id:
                candidate = item
                break
            if self.select_candidate_type is not None and item.candidate_type == self.select_candidate_type:
                candidate = item
                break
        action = "RESUME_TASK" if str(candidate.candidate_type) == "SUSPENDED_TASK_RESUME" else "START_SOP"
        return ClassifierResult(
            selected_action=action,
            selected_candidate_id=candidate.candidate_id,
            confidence=candidate.score,
            rationale="recording classifier",
            needs_clarification=False,
            clarification_question=None,
        )


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_semantic_policy.db"
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
