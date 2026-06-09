import tempfile
import unittest
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabFaqExactPolicyTest(unittest.TestCase):
    def test_no_active_exact_faq_answers_before_sop_arbitration(self) -> None:
        with _session() as session:
            faq_gate = _StaticFaqGate(_child_ticket_refund_proposal())
            service = RuntimeLabService(RuntimeLabRepository(session), faq_answer_gate=faq_gate)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "儿童票可以退吗？")

            self.assertEqual(turn.reply, "儿童票如未使用可按客票规则申请退票。")
            self.assertEqual(turn.route_decision.action, "ANSWER_FAQ")
            self.assertEqual(turn.route_decision.faq_answer["sourceLayer"], "faq_exact")
            self.assertEqual(turn.route_decision.faq_answer["evidence"]["faqId"], 12)
            self.assertIsNone(turn.active_task)
            self.assertEqual(turn.suspended_tasks, [])
            self.assertIsNotNone(turn.route_decision.classifier_request)
            self.assertEqual(turn.route_decision.policy_gate["stage"], "post_classifier")
            event_types = [event["event_type"] for event in turn.events]
            self.assertIn("FAQ_ANSWERED", event_types)
            self.assertEqual(faq_gate.messages, ["儿童票可以退吗？"])

    def test_explicit_handoff_mixed_with_faq_wins_before_faq_gate(self) -> None:
        with _session() as session:
            faq_gate = _StaticFaqGate(_child_ticket_refund_proposal())
            service = RuntimeLabService(RuntimeLabRepository(session), faq_answer_gate=faq_gate)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "我要人工客服，儿童票可以退吗？")

            self.assertEqual(turn.route_decision.action, "HANDOFF_TO_HUMAN")
            self.assertEqual(turn.route_decision.handoff["reasonCode"], "USER_REQUEST")
            self.assertEqual(faq_gate.messages, [])

    def test_active_sop_exact_faq_answer_preserves_task_checkpoint_and_business_refs(self) -> None:
        with _session() as session:
            faq_gate = _StaticFaqGate(_child_ticket_refund_proposal())
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository, faq_answer_gate=faq_gate)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            started = service.handle_message(session_id, "我要退票")
            before = dict(started.active_task)
            answered = service.handle_message(session_id, "儿童票可以退吗？")
            after_checkpoint = repository.get_latest_checkpoint(int(before["id"]))

            self.assertEqual(answered.route_decision.action, "ANSWER_FAQ")
            self.assertEqual(answered.reply, "儿童票如未使用可按客票规则申请退票。")
            self.assertEqual(answered.active_task["id"], before["id"])
            self.assertEqual(answered.active_task["current_step"], before["current_step"])
            self.assertEqual(answered.active_task["checkpoint_id"], before["checkpoint_id"])
            self.assertEqual(answered.active_task["business_refs"], before["business_refs"])
            self.assertEqual(after_checkpoint["id"], before["checkpoint_id"])
            self.assertNotIn("TASK_CONTINUED", [event["event_type"] for event in answered.events])

    def test_active_sop_ambiguous_faq_and_slot_input_clarifies_without_task_mutation(self) -> None:
        with _session() as session:
            faq_gate = _StaticFaqGate(_child_ticket_refund_proposal())
            service = RuntimeLabService(RuntimeLabRepository(session), faq_answer_gate=faq_gate)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            started = service.handle_message(session_id, "我要退票")
            before = dict(started.active_task)
            clarified = service.handle_message(session_id, "儿童票可以退吗？订单TK-100")

            self.assertEqual(clarified.route_decision.action, "CLARIFY")
            self.assertEqual(clarified.route_decision.faq_answer["reasonCode"], "AMBIGUOUS_ACTIVE_SOP")
            self.assertEqual(clarified.active_task["id"], before["id"])
            self.assertEqual(clarified.active_task["current_step"], before["current_step"])
            self.assertEqual(clarified.active_task["checkpoint_id"], before["checkpoint_id"])
            self.assertNotIn("TASK_CONTINUED", [event["event_type"] for event in clarified.events])


def _session() -> Session:
    tmp_dir = tempfile.TemporaryDirectory()
    db_path = Path(tmp_dir.name) / "runtime_lab_faq_exact_policy.db"
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


def _child_ticket_refund_proposal() -> FaqAnswerProposal:
    return FaqAnswerProposal(
        answer="儿童票如未使用可按客票规则申请退票。",
        confidence=1.0,
        margin=1.0,
        evidence=FaqAnswerEvidence(
            faq_id=12,
            question="儿童票可以退吗？",
            answer="儿童票如未使用可按客票规则申请退票。",
            score=2.0,
            match_type="EXACT",
            source="structured_faq",
            matched_terms=("儿童票可以退吗",),
        ),
    )


class _StaticFaqGate:
    def __init__(self, proposal: FaqAnswerProposal | None) -> None:
        self._proposal = proposal
        self.messages: list[str] = []

    def propose(
        self,
        message: str,
        *,
        active_task: dict | None,
        suspended_tasks: list[dict],
    ) -> FaqAnswerProposal | None:
        self.messages.append(message)
        if "儿童票" not in message:
            return None
        return self._proposal
