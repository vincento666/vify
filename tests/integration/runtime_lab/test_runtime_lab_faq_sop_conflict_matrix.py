from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.faq_gate import FaqAnswerEvidence, FaqAnswerProposal, RuntimeAirlineFaqGate
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabFaqSopConflictMatrixTest(unittest.TestCase):
    def test_faq_sop_conflict_enters_one_central_arbitration_pool(self) -> None:
        with _session() as session:
            classifier = _FaqFirstClassifier()
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                faq_answer_gate=_StaticFaqGate(_child_ticket_refund_proposal()),
                classifier=classifier,
            )
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我要退票，先问一下儿童票可以退吗？")

            self.assertEqual(turn.route_decision.action, "ANSWER_FAQ")
            self.assertTrue(classifier.inputs, "FAQ/SOP conflict must reach central arbitration")
            candidate_types = {str(candidate.candidate_type) for candidate in classifier.inputs[-1].candidates}
            self.assertIn("ANSWER_FAQ", candidate_types)
            self.assertIn("SOP_INTENT", candidate_types)
            self.assertEqual(turn.route_decision.policy_gate["stage"], "post_classifier")

    def test_no_active_consultation_hits_faq_but_transaction_starts_sop(self) -> None:
        cases = (
            ("儿童票如果临时不飞了可以退吗？", "ANSWER_FAQ", None),
            ("我要办理儿童票退票，订单号CA1001，手机号13500000001，乘机人张三", "START_SOP", "refund_ticket"),
            ("行李额怎么看？免费托运有多少", "ANSWER_FAQ", None),
            ("行李可能超重，能不能提前买一点额度，订单号CA1002", "START_SOP", "baggage_service"),
            ("改签手续费怎么算？", "ANSWER_FAQ", None),
            ("我要改签刚才那张票到明天上午，手续费也一起看下", "START_SOP", "change_flight"),
            ("我只是想问团队票如果临时有人不飞，退票手续费怎么算？现在不办理", "ANSWER_FAQ", None),
        )
        for message, action, sop_id in cases:
            with self.subTest(message=message):
                with _session() as session:
                    classifier = _SwitchAwareClassifier(selected_target_id=sop_id)
                    service = RuntimeLabService(
                        RuntimeLabRepository(session),
                        faq_answer_gate=RuntimeAirlineFaqGate(),
                        classifier=classifier,
                    )
                    runtime_session = service.create_session()

                    turn = service.handle_message(int(runtime_session["id"]), message)

                    self.assertEqual(turn.route_decision.action, action)
                    if sop_id is None:
                        self.assertIsNone(turn.active_task)
                        self.assertEqual(turn.route_decision.faq_answer["sourceLayer"], "runtime_airline_faq")
                    else:
                        self.assertEqual(turn.active_task["sop_id"], sop_id)
                        self.assertIsNone(turn.route_decision.faq_answer)

    def test_active_sop_pure_faq_preserves_task_but_transaction_switches_or_continues(self) -> None:
        cases = (
            ("儿童票可以退吗？", "ANSWER_FAQ", "flight_booking", "flight_booking"),
            ("我要退另一张票，订单号CA9999，手机号13515151515，乘机人王五", "SUSPEND_AND_START", "flight_booking", "refund_ticket"),
            ("行李额怎么看？免费托运有多少", "ANSWER_FAQ", "flight_booking", "flight_booking"),
            ("我要给这张票加购20公斤行李额，订单号CA1003", "SUSPEND_AND_START", "flight_booking", "baggage_service"),
            ("改签手续费怎么算？", "ANSWER_FAQ", "refund_ticket", "refund_ticket"),
            ("我要改签刚才那张票到明天上午，手续费也一起看下", "SUSPEND_AND_START", "refund_ticket", "change_flight"),
        )
        for message, action, active_sop, expected_active_sop in cases:
            with self.subTest(message=message):
                with _session() as session:
                    classifier = _SwitchAwareClassifier(selected_target_id=expected_active_sop)
                    repository = RuntimeLabRepository(session)
                    service = RuntimeLabService(
                        repository,
                        faq_answer_gate=RuntimeAirlineFaqGate(),
                        classifier=classifier,
                    )
                    runtime_session = service.create_session()
                    session_id = int(runtime_session["id"])

                    service.handle_message(session_id, _start_message(active_sop))
                    before = dict(repository.get_active_task(session_id))
                    turn = service.handle_message(session_id, message)
                    after = repository.get_active_task(session_id)

                    self.assertEqual(turn.route_decision.action, action)
                    self.assertEqual(after["sop_id"], expected_active_sop)
                    if action == "ANSWER_FAQ":
                        self.assertEqual(after["id"], before["id"])
                        self.assertEqual(after["checkpoint_id"], before["checkpoint_id"])
                        self.assertEqual(turn.route_decision.faq_answer["sourceLayer"], "runtime_airline_faq")
                    else:
                        self.assertNotEqual(after["id"], before["id"])
                        self.assertIsNone(turn.route_decision.faq_answer)

    def test_llm_clarify_on_active_faq_is_recovered_without_mutating_task(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            start_service = RuntimeLabService(
                repository,
                faq_answer_gate=RuntimeAirlineFaqGate(),
                classifier=_SwitchAwareClassifier(selected_target_id="baggage_service"),
            )
            service = RuntimeLabService(
                repository,
                faq_answer_gate=RuntimeAirlineFaqGate(),
                classifier=_ClarifyClassifier(),
            )
            runtime_session = start_service.create_session()
            session_id = int(runtime_session["id"])

            start_service.handle_message(session_id, "我出差可能两个箱子超重，先帮我看下能不能加行李，订单号等会给")
            before = dict(repository.get_active_task(session_id))
            turn = service.handle_message(session_id, "随身行李和托运行李额度怎么算？先问问规则")
            after = repository.get_active_task(session_id)

            self.assertEqual(turn.route_decision.action, "ANSWER_FAQ")
            self.assertEqual(turn.route_decision.classifier_result["selected_action"], "ANSWER_FAQ")
            self.assertEqual(turn.route_decision.classifier_result["_debug"]["clarifyRecovery"]["from"], "CLARIFY")
            self.assertEqual(after["id"], before["id"])
            self.assertEqual(after["checkpoint_id"], before["checkpoint_id"])

    def test_pet_material_comparison_faq_is_not_blocked_as_document_comparison(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            start_service = RuntimeLabService(
                repository,
                faq_answer_gate=RuntimeAirlineFaqGate(),
                classifier=_SwitchAwareClassifier(selected_target_id="pet_cabin"),
            )
            service = RuntimeLabService(
                repository,
                faq_answer_gate=RuntimeAirlineFaqGate(),
                classifier=_ClarifyClassifier(),
            )
            runtime_session = start_service.create_session()
            session_id = int(runtime_session["id"])

            start_service.handle_message(session_id, "我下个月想带猫去成都，先办理宠物乘机，航班和证件材料还没定")
            before = dict(repository.get_active_task(session_id))
            turn = service.handle_message(session_id, "宠物进客舱和托运材料有什么区别？只是问清楚")
            after = repository.get_active_task(session_id)

            self.assertEqual(turn.route_decision.action, "ANSWER_FAQ")
            self.assertEqual(turn.route_decision.faq_answer["reasonCode"], "PET_CABIN_DOCS")
            self.assertEqual(after["id"], before["id"])
            self.assertEqual(after["checkpoint_id"], before["checkpoint_id"])


class _SwitchAwareClassifier:
    def __init__(self, selected_target_id: str | None = None) -> None:
        self.selected_target_id = selected_target_id
        self.inputs: list[ClassifierInput] = []

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        self.inputs.append(classifier_input)
        candidate = classifier_input.candidates[0]
        if self.selected_target_id is None or _looks_like_consultation(classifier_input.message):
            for item in classifier_input.candidates:
                if str(item.candidate_type) == "ANSWER_FAQ":
                    candidate = item
                    break
        for item in classifier_input.candidates:
            if self.selected_target_id is not None and item.target_id == self.selected_target_id:
                candidate = item
                break
        active = bool(classifier_input.session_state.get("activeTask"))
        if str(candidate.candidate_type) == "SOP_INTENT":
            action = "SUSPEND_AND_START" if active else "START_SOP"
        elif str(candidate.candidate_type) == "ACTIVE_TASK_CONTINUE":
            action = "CONTINUE_ACTIVE_SOP"
        elif str(candidate.candidate_type) == "SUSPENDED_TASK_RESUME":
            action = "RESUME_TASK"
        elif str(candidate.candidate_type) == "ANSWER_FAQ":
            action = "ANSWER_FAQ"
        else:
            action = "CLARIFY"
        return ClassifierResult(
            selected_action=action,
            selected_candidate_id=candidate.candidate_id if action != "CLARIFY" else None,
            confidence=candidate.score,
            rationale="switch-aware test classifier",
            needs_clarification=False,
            clarification_question=None,
        )


class _ClarifyClassifier:
    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        return ClassifierResult(
            selected_action="CLARIFY",
            selected_candidate_id=None,
            confidence=0.95,
            rationale="test llm returned clarify despite finite answer candidate",
            needs_clarification=True,
            clarification_question="需要澄清",
            arbitrator_mode="llm",
            used_real_llm=True,
            debug={"model": "test-llm"},
        )


class _FaqFirstClassifier:
    def __init__(self) -> None:
        self.inputs: list[ClassifierInput] = []

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        self.inputs.append(classifier_input)
        candidate = next(
            (item for item in classifier_input.candidates if str(item.candidate_type) == "ANSWER_FAQ"),
            classifier_input.candidates[0],
        )
        action = "ANSWER_FAQ" if str(candidate.candidate_type) == "ANSWER_FAQ" else "START_SOP"
        return ClassifierResult(
            selected_action=action,
            selected_candidate_id=candidate.candidate_id,
            confidence=candidate.score,
            rationale="faq-first conflict test classifier",
            needs_clarification=False,
            clarification_question=None,
        )


def _start_message(sop_id: str) -> str:
    return {
        "flight_booking": "下周三上午广州飞上海，先帮我订一张机票，联系方式稍后给你",
        "refund_ticket": "我要办理退票",
    }[sop_id]


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_faq_sop_conflict_matrix", register=register_runtime_lab_tables) as session:
        yield session


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

    def propose(
        self,
        message: str,
        *,
        active_task: dict | None,
        suspended_tasks: list[dict],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        if "儿童票" not in message:
            return None
        return self._proposal


def _looks_like_consultation(message: str) -> bool:
    return any(term in message for term in ("吗", "怎么", "如何", "多少", "规则", "手续费", "免费"))
