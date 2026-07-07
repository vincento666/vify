from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop import mock_sop_manifests
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabSemanticPolicyTest(unittest.TestCase):
    def test_no_active_strong_start_enters_central_arbitration(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier()
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我要退票")

            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "refund_ticket")
            self.assertEqual(classifier.calls, 1)
            self.assertEqual(turn.route_decision.policy_gate["stage"], "post_classifier")

    def test_no_active_conflict_calls_classifier_once_and_starts_selected_sop(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="invoice_apply")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()

            turn = service.handle_message(int(runtime_session["id"]), "我想退费并开发票")

            self.assertEqual(classifier.calls, 1)
            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "invoice_apply")

    def test_message_command_can_override_route_thresholds_for_current_turn_only(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="invoice_apply")
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                classifier=classifier,
                policy_thresholds={"classifierMinConfidence": 0.61, "candidateTopK": 5},
            )
            runtime_session = service.create_session()

            service.handle_command(
                int(runtime_session["id"]),
                "我想退费并开发票",
                idempotency_key="local-thresholds-1",
                policy_thresholds_override={
                    "classifierMinConfidence": 0.77,
                    "candidateTopK": 3,
                },
            )

            self.assertEqual(classifier.inputs[0].thresholds["classifierMinConfidence"], 0.77)
            self.assertEqual(len(classifier.inputs[0].candidates), 3)
            self.assertEqual(service._classifier_min_confidence(), 0.61)

    def test_active_conflict_uses_classifier_before_sop_mutation(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="invoice_apply")
            repository = RuntimeLabRepository(session)
            service = RuntimeLabService(repository, classifier=classifier)
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            turn = service.handle_message(int(runtime_session["id"]), "我想退费并开发票")
            tasks = repository.list_tasks(int(runtime_session["id"]))

            self.assertEqual(classifier.calls, 2)
            self.assertEqual(turn.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(turn.active_task["sop_id"], "invoice_apply")
            self.assertEqual(tasks[0]["sop_id"], "refund_ticket")
            self.assertNotIn("business_refs", tasks[0])

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
            # Spec 213.3.5e bans runtime_lab_task.current_step writes; the durable
            # current_step is resolved into the response projection instead of the
            # DB mirror column.
            self.assertEqual(turn.active_task["current_step"], "confirm")

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

    def test_active_booking_detail_continues_even_when_message_mentions_price_preference(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我明天要接人，想先看看北京到广州的航班会不会延误")
            switched = service.handle_message(
                session_id,
                "先帮我订票吧，明天上午9点左右，北京到广州，一个成人，身份证号我等下给。",
            )
            turn = service.handle_message(
                session_id,
                "张三，身份证 110101199001011234，手机 13800138000，经济舱就行，价格优先。",
            )

            self.assertEqual(switched.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(switched.active_task["sop_id"], "flight_booking")
            self.assertEqual(turn.route_decision.action, "CONTINUE_ACTIVE_SOP")
            self.assertEqual(turn.active_task["sop_id"], "flight_booking")

    def test_active_refund_does_not_swallow_natural_booking_request_as_collection_detail(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要办理退票")
            turn = service.handle_message(session_id, "我想先订上海到广州明天的机票，乘机人王五，手机号13515151515")

            self.assertEqual(turn.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(turn.active_task["sop_id"], "flight_booking")
            self.assertEqual(turn.suspended_tasks[0]["sop_id"], "refund_ticket")

    def test_active_collection_detail_overrides_weak_llm_switch_candidate(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            start_service = RuntimeLabService(
                repository,
                classifier=_RecordingClassifier(selected_target_id="irregular_flight"),
            )
            service = RuntimeLabService(
                repository,
                classifier=_RecordingClassifier(selected_target_id="change_flight"),
            )
            runtime_session = start_service.create_session()
            session_id = int(runtime_session["id"])

            start_service.handle_message(session_id, "刚收到通知航班取消了，先转异常航班处理")
            turn = service.handle_message(session_id, "航班号CA1234，手机号13900139000，乘机人赵六，希望改到明天上午")

            self.assertEqual(turn.route_decision.action, "CONTINUE_ACTIVE_SOP")
            self.assertEqual(turn.active_task["sop_id"], "irregular_flight")
            self.assertEqual(turn.route_decision.active_task_id, turn.active_task["id"])

    def test_active_collection_detail_overrides_erroneous_suspended_resume_candidate(self) -> None:
        with _session() as session:
            repository = RuntimeLabRepository(session)
            start_status_service = RuntimeLabService(
                repository,
                classifier=_RecordingClassifier(selected_target_id="flight_status"),
            )
            switch_service = RuntimeLabService(
                repository,
                classifier=_RecordingClassifier(selected_target_id="irregular_flight"),
            )
            resume_biased_service = RuntimeLabService(
                repository,
                classifier=_RecordingClassifier(select_candidate_type="SUSPENDED_TASK_RESUME"),
            )
            runtime_session = start_status_service.create_session()
            session_id = int(runtime_session["id"])

            start_status_service.handle_message(session_id, "司机在机场等我，我想查一下航班现在到哪了，航班号等会发")
            switch_service.handle_message(session_id, "刚收到通知航班取消了，先转异常航班处理")
            turn = resume_biased_service.handle_message(
                session_id,
                "航班号CA1234，手机号13900139000，乘机人赵六，希望改到明天上午",
            )

            self.assertEqual(turn.route_decision.action, "CONTINUE_ACTIVE_SOP")
            self.assertEqual(turn.active_task["sop_id"], "irregular_flight")
            self.assertEqual(turn.suspended_tasks[0]["sop_id"], "flight_status")

    def test_enabled_scope_weak_booking_signal_limits_llm_candidates(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="flight_booking")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])
            enabled_sop_ids = tuple(mock_sop_manifests())

            turn = service.handle_message(
                session_id,
                "我要订广州飞北京的航班",
                enabled_sop_ids=enabled_sop_ids,
            )

            self.assertEqual(classifier.calls, 1)
            self.assertLess(len(classifier.inputs[0].candidates), len(enabled_sop_ids))
            self.assertLessEqual(len(classifier.inputs[0].candidates), 5)
            self.assertIn("flight_booking", {candidate.target_id for candidate in classifier.inputs[0].candidates})
            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "flight_booking")
            self.assertNotIn("暂未匹配", turn.reply)
            self.assertNotIn("enabled_scope_fallback", turn.route_decision.candidate_sources)

    def test_enabled_scope_zero_recall_generic_message_clarifies_without_full_llm_fallback(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier()
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(
                session_id,
                "我有个航旅相关的问题想处理，先帮我判断该走哪个流程",
                enabled_sop_ids=tuple(mock_sop_manifests()),
            )

            self.assertEqual(classifier.calls, 0)
            self.assertEqual(turn.route_decision.action, "CLARIFY")
            self.assertEqual(turn.route_decision.policy_gate["stage"], "no_signal_clarify")
            self.assertEqual(turn.route_decision.classifier_request, None)
            self.assertEqual(turn.route_decision.candidates, [])

    def test_enabled_scope_empty_recall_can_clarify_when_arbitrator_cannot_identify(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(
                session_id,
                "你好，今天心情不错",
                enabled_sop_ids=("flight_booking", "refund_ticket"),
            )

            self.assertEqual(turn.route_decision.action, "CLARIFY")
            self.assertIn("订票", turn.reply)

    def test_global_weak_booking_signal_limits_llm_candidates(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="flight_booking")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(
                session_id,
                "这周工作临时排开了，想看看广州去北京明天上午的航班还能不能订，乘机人张三，用 13800138000 联系",
            )

            self.assertEqual(classifier.calls, 1)
            self.assertLess(len(classifier.inputs[0].candidates), len(mock_sop_manifests()))
            self.assertLessEqual(len(classifier.inputs[0].candidates), 5)
            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "flight_booking")
            self.assertNotIn("finite_intent_fallback", turn.route_decision.candidate_sources)
            self.assertNotIn("暂未匹配", turn.reply)

    def test_natural_booking_arrange_one_ticket_signal_recalls_booking(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="flight_booking")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(
                session_id,
                "这周工作临时排开了，想看看广州去北京明天上午的航班还能不能安排一张，乘机人张三，用 13800138000 联系",
            )

            self.assertEqual(classifier.calls, 1)
            self.assertIn("flight_booking", {candidate.target_id for candidate in classifier.inputs[0].candidates})
            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "flight_booking")

    def test_llm_clarify_on_single_flight_status_candidate_recovers_to_start_sop(self) -> None:
        with _session() as session:
            classifier = _ClarifyClassifier()
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "司机在机场等我，我想查一下航班现在到哪了，航班号等会发")

            self.assertEqual(classifier.calls, 1)
            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "flight_status")
            self.assertLessEqual(len(classifier.inputs[0].candidates), 5)
            self.assertIn("flight_status", {candidate.target_id for candidate in classifier.inputs[0].candidates})
            self.assertEqual(turn.route_decision.classifier_result["selected_action"], "START_SOP")
            self.assertEqual(turn.route_decision.classifier_result["_debug"]["clarifyRecovery"]["from"], "CLARIFY")

    def test_uncertain_to_fly_phrase_does_not_match_booking_from_single_ding_character(self) -> None:
        with _session() as session:
            classifier = _RecordingClassifier(selected_target_id="refund_ticket")
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "我不确定今天还能不能飞，这张票款想拿回来，先帮我处理一下")

            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "refund_ticket")
            self.assertEqual(classifier.calls, 1)
            self.assertNotIn("flight_booking", {candidate["target_id"] for candidate in turn.route_decision.candidates or []})

    def test_classifier_failure_degrades_to_clarify_with_evidence(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=_FailingClassifier())
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(
                session_id,
                "我要订广州飞北京的航班",
                enabled_sop_ids=("flight_booking", "refund_ticket"),
            )

            self.assertEqual(turn.route_decision.action, "CLARIFY")
            self.assertIsNone(turn.active_task)
            self.assertEqual(turn.route_decision.policy_gate["stage"], "post_classifier")
            self.assertEqual(turn.route_decision.classifier_result["selected_action"], "CLARIFY")
            self.assertEqual(turn.route_decision.classifier_result["arbitrator_mode"], "classifier_error")
            self.assertIn("Classifier failed", turn.route_decision.reason)

    def test_llm_classifier_failure_uses_deterministic_finite_candidate_fallback(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session), classifier=_FailingLlmClassifier())
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            turn = service.handle_message(session_id, "我暂时不出票，先问下北京到上海周五晚上票价大概多少")

            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.active_task["sop_id"], "fare_quote")
            self.assertEqual(turn.route_decision.classifier_result["arbitrator_mode"], "llm_error_fallback")
            self.assertFalse(turn.route_decision.classifier_result["used_real_llm"])

    def test_duplicate_confirmation_after_completed_task_does_not_start_new_sop(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要改签")
            service.handle_message(session_id, "订单号 CA1003，手机号13800138003，乘机人赵三，改到后天上午")
            service.handle_message(session_id, "确认")
            turn = service.handle_message(session_id, "确认改签")

            self.assertEqual(turn.route_decision.action, "AGENT_FALLBACK")
            self.assertEqual(turn.route_decision.agent_answer["reasonCode"], "RECENT_TASK_ALREADY_COMPLETED")
            self.assertIsNone(turn.active_task)
            self.assertIn("已完成", turn.reply)

    def test_active_task_blocks_suspended_resume_without_server_error(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我明天要接人，想先看看北京到广州的航班会不会延误")
            service.handle_message(
                session_id,
                "先帮我订票吧，明天上午9点左右，北京到广州，一个成人，身份证号我等下给。",
            )
            turn = service.handle_message(session_id, "就查刚订这个 CA1301。")

            self.assertEqual(turn.route_decision.action, "REJECT_SWITCH_SUSPENDED_LIMIT")
            self.assertEqual(turn.active_task["sop_id"], "flight_booking")
            self.assertEqual(turn.suspended_tasks[0]["sop_id"], "flight_status")


class _RecordingClassifier:
    def __init__(
        self,
        selected_target_id: str | None = None,
        select_candidate_type: str | None = None,
    ) -> None:
        self.calls = 0
        self.inputs: list[ClassifierInput] = []
        self.selected_target_id = selected_target_id
        self.select_candidate_type = select_candidate_type

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        self.calls += 1
        self.inputs.append(classifier_input)
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


class _ClarifyClassifier:
    def __init__(self) -> None:
        self.calls = 0
        self.inputs: list[ClassifierInput] = []

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        self.calls += 1
        self.inputs.append(classifier_input)
        return ClassifierResult(
            selected_action="CLARIFY",
            selected_candidate_id=None,
            confidence=0.88,
            rationale="test llm returned clarify despite finite candidate",
            needs_clarification=True,
            clarification_question="需要澄清",
            arbitrator_mode="llm",
            used_real_llm=True,
            debug={"model": "test-llm"},
        )


class _FailingClassifier:
    def classify(self, _classifier_input: ClassifierInput) -> ClassifierResult:
        raise RuntimeError("upstream unavailable")


class _FailingLlmClassifier:
    def classify(self, _classifier_input: ClassifierInput) -> ClassifierResult:
        raise RuntimeError("openrouter unavailable")


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_semantic_policy", register=register_runtime_lab_tables) as session:
        yield session
