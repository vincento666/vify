import unittest

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service


TARGETED_QUESTION = "请确认您要退整张机票，还是只退附加服务？"


class RuntimeLabTargetedClarificationApiContractTest(unittest.TestCase):
    def setUp(self) -> None:
        app.dependency_overrides[get_runtime_lab_service] = _targeted_runtime_service

    def tearDown(self) -> None:
        app.dependency_overrides.pop(get_runtime_lab_service, None)

    def test_public_api_replays_the_same_targeted_question_without_task_mutation(self) -> None:
        with TestClient(app) as client:
            session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
            request = {
                "message": "我要退票",
                "idempotencyKey": "contract-targeted-clarification",
            }

            first = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json=request,
            )
            replay = client.post(
                f"/api/v1/runtime-lab/sessions/{session_id}/messages",
                json=request,
            )
            tasks = client.get(
                f"/api/v1/runtime-lab/sessions/{session_id}/tasks"
            ).json()["data"]["list"]
            events = client.get(
                f"/api/v1/runtime-lab/sessions/{session_id}/events"
            ).json()["data"]["list"]

        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["code"], 200)
        self.assertEqual(first.json()["message"], "success")
        first_data = first.json()["data"]
        replay_data = replay.json()["data"]
        self.assertEqual(first_data["reply"], TARGETED_QUESTION)
        self.assertEqual(
            first_data["routeDecision"]["clarificationQuestion"],
            TARGETED_QUESTION,
        )
        self.assertEqual(replay_data, first_data)
        self.assertEqual(tasks, [])
        self.assertEqual(
            [event["eventType"] for event in events],
            ["SESSION_CREATED", "USER_MESSAGE", "ROUTE_DECISION"],
        )
        self.assertEqual(
            events[-1]["payload"]["clarificationQuestion"],
            TARGETED_QUESTION,
        )


class _TargetedClassifier:
    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        return ClassifierResult(
            selected_action="START_SOP",
            selected_candidate_id=classifier_input.candidates[0].candidate_id,
            confidence=0.59,
            rationale="Scripted low-confidence transactional selection",
            needs_clarification=False,
            clarification_question=TARGETED_QUESTION,
            arbitrator_mode="fixture",
            used_real_llm=False,
        )


def _targeted_runtime_service(
    session: Session = Depends(get_session),
) -> RuntimeLabService:
    return RuntimeLabService(
        RuntimeLabRepository(session),
        classifier=_TargetedClassifier(),
        policy_thresholds={"classifierMinConfidence": 0.6},
    )


if __name__ == "__main__":
    unittest.main()
