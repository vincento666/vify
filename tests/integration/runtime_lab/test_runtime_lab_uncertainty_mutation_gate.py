from collections.abc import Iterator
from contextlib import contextmanager
import math
import unittest

from sqlalchemy.orm import Session

from app.modules.runtime_lab.domain.classifier import (
    ClassifierInput,
    ClassifierResult,
    LlmConstrainedIntentClassifier,
)
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import (
    FakeSopRuntimeAdapter,
    SopExecutionRequest,
    SopExecutionResult,
)
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.infra.schema import register_runtime_lab_tables
from tests.support.mysql import mysql8_session


class RuntimeLabUncertaintyMutationGateTest(unittest.TestCase):
    def test_every_uncertainty_branch_clarifies_without_task_or_adapter_mutation(self) -> None:
        cases: dict[str, object] = {
            "below threshold": _ScriptedClassifier(confidence=0.59),
            "not finite": _ScriptedClassifier(confidence=math.nan),
            "not numeric": _ScriptedClassifier(confidence="invalid"),
            "negative": _ScriptedClassifier(confidence=-0.1),
            "above one": _ScriptedClassifier(confidence=1.1),
            "explicit clarification": _ScriptedClassifier(needs_clarification=True),
            "outside candidate pool": _ScriptedClassifier(selected_candidate_id="sop:invented"),
            "incoherent clarify": _ScriptedClassifier(
                selected_action="CLARIFY",
                selected_candidate_id=None,
                needs_clarification=False,
            ),
            "malformed llm confidence": LlmConstrainedIntentClassifier(
                lambda _payload: {
                    "selected_action": "START_SOP",
                    "selected_candidate_id": "sop:refund_ticket",
                    "confidence": "low",
                    "rationale": "malformed real classifier confidence",
                    "needs_clarification": False,
                    "clarification_question": None,
                }
            ),
        }

        with _session() as session:
            for name, classifier in cases.items():
                with self.subTest(name=name):
                    repository = RuntimeLabRepository(session)
                    adapter = _RecordingAdapter()
                    service = RuntimeLabService(
                        repository,
                        adapter=adapter,
                        classifier=classifier,
                        policy_thresholds={"classifierMinConfidence": 0.6},
                    )
                    runtime_session = service.create_session()
                    session_id = int(runtime_session["id"])

                    turn = service.handle_message(session_id, "我要退票")

                    self.assertEqual(turn.route_decision.action, "CLARIFY")
                    self.assertEqual(repository.list_tasks(session_id), [])
                    self.assertEqual(adapter.start_calls, 0)
                    self.assertNotIn(
                        "TASK_STARTED",
                        [event["event_type"] for event in repository.list_events(session_id)],
                    )

    def test_targeted_question_survives_event_and_idempotent_command_replay_without_mutation(self) -> None:
        cases = {
            "low confidence transactional selection": _ScriptedClassifier(
                confidence=0.59,
                clarification_question="  请确认您要退整张机票，还是只退附加服务？  ",
            ),
            "high confidence explicit clarification": _ScriptedClassifier(
                confidence=0.95,
                needs_clarification=True,
                clarification_question="请确认您想办理退票，还是先查询退票规则？",
            ),
        }

        with _session() as session:
            for index, (name, classifier) in enumerate(cases.items(), start=1):
                with self.subTest(name=name):
                    repository = RuntimeLabRepository(session)
                    adapter = _RecordingAdapter()
                    service = RuntimeLabService(
                        repository,
                        adapter=adapter,
                        classifier=classifier,
                        policy_thresholds={"classifierMinConfidence": 0.6},
                    )
                    runtime_session = service.create_session()
                    session_id = int(runtime_session["id"])
                    idempotency_key = f"targeted-clarify-{index}"

                    first = service.handle_command(
                        session_id,
                        "我要退票",
                        idempotency_key=idempotency_key,
                    )
                    replay = service.handle_command(
                        session_id,
                        "我要退票",
                        idempotency_key=idempotency_key,
                    )
                    events = repository.list_events(session_id)
                    route_event = next(event for event in events if event["event_type"] == "ROUTE_DECISION")

                    expected_question = classifier.clarification_question.strip()
                    self.assertEqual(first.payload["reply"], expected_question)
                    self.assertEqual(
                        first.payload["routeDecision"]["clarificationQuestion"],
                        expected_question,
                    )
                    self.assertEqual(
                        route_event["payload"]["clarificationQuestion"],
                        expected_question,
                    )
                    self.assertFalse(first.replayed)
                    self.assertTrue(replay.replayed)
                    self.assertEqual(replay.payload, first.payload)
                    self.assertEqual(repository.list_tasks(session_id), [])
                    self.assertEqual(adapter.start_calls, 0)
                    self.assertEqual(
                        [event["event_type"] for event in events],
                        ["SESSION_CREATED", "USER_MESSAGE", "ROUTE_DECISION"],
                    )

    def test_blank_question_uses_existing_generic_menu(self) -> None:
        generic_menu = (
            "请问您想办理订票、票价、团队票、增值服务、退票、改签、资料修改、发票、行李、"
            "值机、航班动态、特殊协助、宠物乘机、异常航班还是会员里程？"
        )

        with _session() as session:
            repository = RuntimeLabRepository(session)
            adapter = _RecordingAdapter()
            service = RuntimeLabService(
                repository,
                adapter=adapter,
                classifier=_ScriptedClassifier(
                    confidence=0.95,
                    needs_clarification=True,
                    clarification_question=" \n\t ",
                ),
                policy_thresholds={"classifierMinConfidence": 0.6},
            )
            session_id = int(service.create_session()["id"])

            result = service.handle_command(
                session_id,
                "我要退票",
                idempotency_key="blank-clarify-fallback",
            )

            self.assertEqual(result.payload["reply"], generic_menu)
            self.assertEqual(
                result.payload["routeDecision"]["clarificationQuestion"],
                generic_menu,
            )
            self.assertEqual(repository.list_tasks(session_id), [])
            self.assertEqual(adapter.start_calls, 0)


class _ScriptedClassifier:
    def __init__(
        self,
        *,
        selected_action: str = "START_SOP",
        selected_candidate_id: str | None = None,
        confidence: object = 0.88,
        needs_clarification: bool = False,
        clarification_question: str | None = None,
    ) -> None:
        self._selected_action = selected_action
        self._selected_candidate_id = selected_candidate_id
        self._confidence = confidence
        self._needs_clarification = needs_clarification
        self.clarification_question = clarification_question

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        selected_candidate_id = self._selected_candidate_id
        if selected_candidate_id is None and self._selected_action != "CLARIFY":
            selected_candidate_id = classifier_input.candidates[0].candidate_id
        return ClassifierResult(
            selected_action=self._selected_action,
            selected_candidate_id=selected_candidate_id,
            confidence=self._confidence,  # type: ignore[arg-type]
            rationale="scripted real classifier",
            needs_clarification=self._needs_clarification,
            clarification_question=self.clarification_question,
            arbitrator_mode="llm",
            used_real_llm=True,
        )


class _RecordingAdapter(FakeSopRuntimeAdapter):
    def __init__(self) -> None:
        super().__init__()
        self.start_calls = 0

    def start_sop(self, request: SopExecutionRequest) -> SopExecutionResult:
        self.start_calls += 1
        return super().start_sop(request)


@contextmanager
def _session() -> Iterator[Session]:
    with mysql8_session("runtime_lab_uncertainty_gate", register=register_runtime_lab_tables) as session:
        yield session


if __name__ == "__main__":
    unittest.main()
