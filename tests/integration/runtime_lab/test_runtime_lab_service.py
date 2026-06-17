from contextlib import contextmanager
import unittest
from collections.abc import Iterator

from sqlalchemy.orm import Session

from tests.support.mysql import mysql8_session
from app.modules.runtime_lab.domain.agent_fallback import FakeFallbackAgent
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import (
    SopCheckpoint,
    SopExecutionRequest,
    SopExecutionResult,
    SopExecutionStatus,
)
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables


class RuntimeLabServiceTest(unittest.TestCase):
    def test_interruptible_switch_suspends_active_task_and_offers_resume_after_completion(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()

            started = service.handle_message(int(runtime_session["id"]), "我要退票")
            switched = service.handle_message(int(runtime_session["id"]), "我要开发票")
            service.handle_message(int(runtime_session["id"]), "INV-200")
            completed = service.handle_message(int(runtime_session["id"]), "确认")

            self.assertEqual(started.route_decision.action, "START_SOP")
            self.assertEqual(switched.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(switched.active_task["sop_id"], "invoice_apply")
            self.assertEqual(switched.suspended_tasks[0]["sop_id"], "refund_ticket")
            self.assertEqual(completed.route_decision.action, "COMPLETE_TASK")
            self.assertIsNotNone(completed.resume_offer)
            self.assertEqual(completed.resume_offer["taskId"], switched.suspended_tasks[0]["id"])
            self.assertEqual(
                [event["event_type"] for event in completed.events],
                [
                    "SESSION_CREATED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_STARTED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_SUSPENDED",
                    "TASK_STARTED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_CONTINUED",
                    "USER_MESSAGE",
                    "ROUTE_DECISION",
                    "TASK_COMPLETED",
                    "RESUME_OFFERED",
                ],
            )

    def test_rejects_switch_at_confirm_step_and_when_one_task_already_suspended(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            service.handle_message(int(runtime_session["id"]), "TK-100")
            rejected_at_confirm = service.handle_message(int(runtime_session["id"]), "我要改签")

            self.assertEqual(rejected_at_confirm.route_decision.action, "REJECT_SWITCH_CONTINUE_ACTIVE")
            self.assertEqual(rejected_at_confirm.active_task["sop_id"], "refund_ticket")
            self.assertEqual(rejected_at_confirm.active_task["current_step"], "confirm")
            self.assertEqual(len(rejected_at_confirm.suspended_tasks), 0)

        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()

            service.handle_message(int(runtime_session["id"]), "我要退票")
            service.handle_message(int(runtime_session["id"]), "我要开发票")
            rejected_by_limit = service.handle_message(int(runtime_session["id"]), "我要改签")

            self.assertEqual(rejected_by_limit.route_decision.action, "REJECT_SWITCH_SUSPENDED_LIMIT")
            self.assertEqual(rejected_by_limit.active_task["sop_id"], "invoice_apply")
            self.assertEqual([task["sop_id"] for task in rejected_by_limit.suspended_tasks], ["refund_ticket"])

    def test_active_booking_collect_does_not_swallow_explicit_refund_request_with_slots(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "下周三上午广州飞上海，先帮我订一张机票，联系方式稍后给你")
            switched = service.handle_message(
                session_id,
                "先不补订票信息了，我要退另一张票，订单号CA9999-20240601-1234，手机号13515151515，乘机人王五",
            )

            self.assertEqual(switched.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(switched.active_task["sop_id"], "refund_ticket")
            self.assertEqual([task["sop_id"] for task in switched.suspended_tasks], ["flight_booking"])

    def test_resume_offer_phrases_restore_suspended_task_checkpoint(self) -> None:
        for phrase in ("继续", "继续刚才", "继续第一个"):
            with self.subTest(phrase=phrase):
                with _session() as session:
                    service = RuntimeLabService(RuntimeLabRepository(session))
                    runtime_session = service.create_session()

                    service.handle_message(int(runtime_session["id"]), "我要退票")
                    service.handle_message(int(runtime_session["id"]), "我要开发票")
                    service.handle_message(int(runtime_session["id"]), "INV-200")
                    service.handle_message(int(runtime_session["id"]), "确认")
                    resumed = service.handle_message(int(runtime_session["id"]), phrase)

                    self.assertEqual(resumed.route_decision.action, "RESUME_TASK")
                    self.assertEqual(resumed.active_task["sop_id"], "refund_ticket")
                    self.assertEqual(resumed.active_task["current_step"], "collect_order_no")
                    self.assertEqual(resumed.suspended_tasks, [])
                    self.assertIsNone(resumed.resume_offer)
                    self.assertEqual(resumed.events[-1]["event_type"], "TASK_RESUMED")

    def test_described_resume_phrase_restores_suspended_task_instead_of_starting_new_sop(self) -> None:
        with _session() as session:
            service = RuntimeLabService(RuntimeLabRepository(session))
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "我要开发票")
            service.handle_message(session_id, "INV-200")
            service.handle_message(session_id, "确认")
            resumed = service.handle_message(session_id, "继续刚才的订票")

            self.assertEqual(resumed.route_decision.action, "RESUME_TASK")
            self.assertEqual(resumed.active_task["sop_id"], "flight_booking")
            self.assertEqual([task["sop_id"] for task in resumed.suspended_tasks], [])

    def test_new_sop_start_inherits_completed_session_business_context(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            completed = service.handle_message(session_id, "确认")
            switched = service.handle_message(session_id, "我想改签刚才的机票")

            self.assertEqual(completed.route_decision.action, "COMPLETE_TASK")
            self.assertEqual(switched.route_decision.action, "START_SOP")
            self.assertEqual(switched.active_task["sop_id"], "change_flight")
            change_request = adapter.start_requests[-1]
            self.assertEqual(change_request.sop_id, "change_flight")
            self.assertEqual(change_request.collected["order_no"], "CA1301-20231027-8899")
            self.assertEqual(change_request.collected["phone"], "13800138000")
            self.assertEqual(change_request.collected["passenger_name"], "张三")
            self.assertEqual(
                change_request.metadata["history"],
                [
                    {"role": "user", "content": "我要订机票"},
                    {"role": "user", "content": "确认"},
                ],
            )
            self.assertTrue(change_request.metadata["contextReference"])
            self.assertEqual(change_request.metadata["inheritedContext"]["passenger_name"], "张三")

    def test_new_sop_start_does_not_default_inherit_when_user_mentions_another_person(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            switched = service.handle_message(session_id, "我要给另一个人改签机票")

            self.assertEqual(switched.route_decision.action, "START_SOP")
            self.assertEqual(switched.active_task["sop_id"], "change_flight")
            change_request = adapter.start_requests[-1]
            self.assertEqual(change_request.sop_id, "change_flight")
            self.assertEqual(change_request.collected, {})
            self.assertFalse(change_request.metadata["contextReference"])
            self.assertNotIn("history", change_request.metadata)
            self.assertEqual(change_request.metadata["inheritedContext"]["passenger_name"], "张三")

    def test_new_sop_start_inherits_context_for_same_trip_reference(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            switched = service.handle_message(session_id, "我还想带宠物一起走，帮我办理宠物乘机")

            self.assertEqual(switched.route_decision.action, "START_SOP")
            self.assertEqual(switched.active_task["sop_id"], "pet_cabin")
            pet_request = adapter.start_requests[-1]
            self.assertEqual(pet_request.sop_id, "pet_cabin")
            self.assertTrue(pet_request.metadata["contextReference"])
            self.assertEqual(pet_request.collected["order_no"], "CA1301-20231027-8899")
            self.assertEqual(pet_request.collected["phone"], "13800138000")
            self.assertEqual(pet_request.collected["passenger_name"], "张三")

    def test_active_sop_continue_can_fill_referenced_slots_from_older_completed_task_context(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "我要团队订票")
            refund_started = service.handle_message(session_id, "我要办理退票")
            service.handle_message(session_id, "退刚才订的那张票")

            self.assertEqual(refund_started.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(refund_started.active_task["sop_id"], "refund_ticket")
            refund_continue_request = adapter.continue_requests[-1]
            self.assertEqual(refund_continue_request.sop_id, "refund_ticket")
            self.assertTrue(refund_continue_request.metadata["contextReference"])
            self.assertEqual(refund_continue_request.collected["order_no"], "CA1301-20231027-8899")
            self.assertEqual(refund_continue_request.collected["phone"], "13800138000")
            self.assertEqual(refund_continue_request.collected["passenger_name"], "张三")
            self.assertNotIn("passenger_count", refund_continue_request.collected)
            self.assertNotIn("passenger_count", refund_continue_request.metadata["inheritedContext"])
            assert refund_continue_request.checkpoint is not None
            self.assertEqual(refund_continue_request.checkpoint.collected["order_no"], "CA1301-20231027-8899")

    def test_pause_active_sop_phrase_does_not_swallow_switch_request(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            service.handle_message(session_id, "我要团队订票")
            switched = service.handle_message(session_id, "先暂停团队票，我要退刚才订的那张票")

            self.assertEqual(switched.route_decision.action, "SUSPEND_AND_START")
            self.assertEqual(switched.active_task["sop_id"], "refund_ticket")
            self.assertEqual(switched.suspended_tasks[0]["sop_id"], "group_booking")
            refund_request = adapter.start_requests[-1]
            self.assertEqual(refund_request.sop_id, "refund_ticket")
            self.assertTrue(refund_request.metadata["contextReference"])
            self.assertEqual(refund_request.collected["order_no"], "CA1301-20231027-8899")
            self.assertEqual(refund_request.collected["phone"], "13800138000")
            self.assertEqual(refund_request.collected["passenger_name"], "张三")

    def test_resume_suspended_sop_does_not_default_fill_slots_from_completed_task_context(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要办理退票")
            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            resumed = service.handle_message(session_id, "继续刚才")

            self.assertEqual(resumed.route_decision.action, "RESUME_TASK")
            self.assertEqual(resumed.active_task["sop_id"], "refund_ticket")
            refund_resume_request = adapter.resume_requests[-1]
            self.assertEqual(refund_resume_request.sop_id, "refund_ticket")
            self.assertFalse(refund_resume_request.metadata["contextReference"])
            self.assertEqual(refund_resume_request.message, "继续刚才")
            self.assertNotIn("order_no", refund_resume_request.collected)
            self.assertNotIn("phone", refund_resume_request.collected)
            self.assertNotIn("passenger_name", refund_resume_request.collected)
            assert refund_resume_request.checkpoint is not None
            self.assertNotIn("order_no", refund_resume_request.checkpoint.collected)

    def test_resume_suspended_sop_can_fill_slots_when_user_references_completed_ticket(self) -> None:
        with _session() as session:
            adapter = _RecordingContextAdapter()
            service = RuntimeLabService(RuntimeLabRepository(session), adapter=adapter)
            runtime_session = service.create_session()
            session_id = int(runtime_session["id"])

            service.handle_message(session_id, "我要办理退票")
            service.handle_message(session_id, "我要订机票")
            service.handle_message(session_id, "确认")
            resumed = service.handle_message(session_id, "继续刚才，退刚订的那张票")

            self.assertEqual(resumed.route_decision.action, "RESUME_TASK")
            refund_resume_request = adapter.resume_requests[-1]
            self.assertTrue(refund_resume_request.metadata["contextReference"])
            self.assertEqual(refund_resume_request.collected["order_no"], "CA1301-20231027-8899")
            self.assertEqual(refund_resume_request.collected["phone"], "13800138000")
            self.assertEqual(refund_resume_request.collected["passenger_name"], "张三")

    def test_natural_booking_request_uses_finite_sop_arbitration_before_agent_fallback(self) -> None:
        with _session() as session:
            service = RuntimeLabService(
                RuntimeLabRepository(session),
                fallback_agent=FakeFallbackAgent(),
            )
            runtime_session = service.create_session()

            turn = service.handle_message(
                int(runtime_session["id"]),
                "我下周要去北京开会，想看看广州飞北京周二上午有没有合适的航班，乘机人李雷，手机13800138000",
            )

            self.assertEqual(turn.route_decision.action, "START_SOP")
            self.assertEqual(turn.route_decision.target_sop_id, "flight_booking")
            self.assertIn("sop_hybrid_recall", turn.route_decision.candidate_sources or [])
            self.assertLessEqual(len(turn.route_decision.classifier_request["candidates"]), 5)
            self.assertNotIn("AGENT_FALLBACK", {candidate["candidate_type"] for candidate in turn.route_decision.classifier_request["candidates"]})


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_service", register=register_runtime_lab_tables) as session:
        yield session


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
