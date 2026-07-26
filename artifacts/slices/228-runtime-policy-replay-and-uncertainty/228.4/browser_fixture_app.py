from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.main import app
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import get_runtime_lab_service


LOW_QUESTION = "请确认您要退整张机票，还是只退附加服务？"
EXPLICIT_QUESTION = "请确认您想办理退票，还是先查询退票规则？"


class BrowserFixtureClassifier:
    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        message = classifier_input.message
        candidate_id = classifier_input.candidates[0].candidate_id
        if "BROWSER_LOW_CONFIDENCE" in message:
            return ClassifierResult(
                selected_action="START_SOP",
                selected_candidate_id=candidate_id,
                confidence=0.59,
                rationale="Browser fixture low-confidence transactional selection",
                needs_clarification=False,
                clarification_question=LOW_QUESTION,
                arbitrator_mode="fixture",
                used_real_llm=False,
            )
        if "BROWSER_EXPLICIT_CLARIFICATION" in message:
            return ClassifierResult(
                selected_action="CLARIFY",
                selected_candidate_id=candidate_id,
                confidence=0.95,
                rationale="Browser fixture explicit clarification",
                needs_clarification=True,
                clarification_question=EXPLICIT_QUESTION,
                arbitrator_mode="fixture",
                used_real_llm=False,
            )
        if "BROWSER_BLANK_QUESTION" in message:
            return ClassifierResult(
                selected_action="CLARIFY",
                selected_candidate_id=candidate_id,
                confidence=0.95,
                rationale="Browser fixture blank clarification",
                needs_clarification=True,
                clarification_question=" \n\t ",
                arbitrator_mode="fixture",
                used_real_llm=False,
            )
        if "BROWSER_IDEMPOTENT_REPLAY" in message:
            return ClassifierResult(
                selected_action="START_SOP",
                selected_candidate_id=candidate_id,
                confidence=0.59,
                rationale="Browser fixture idempotent low-confidence replay",
                needs_clarification=False,
                clarification_question=LOW_QUESTION,
                arbitrator_mode="fixture",
                used_real_llm=False,
            )
        raise AssertionError(f"Unexpected browser fixture message: {message}")


class BrowserRuntimeLabService(RuntimeLabService):
    def handle_command(
        self,
        session_id: int,
        message: str,
        idempotency_key: str | None = None,
        **kwargs: object,
    ):
        if "BROWSER_" in message:
            kwargs["classifier_override"] = None
            kwargs["policy_thresholds_override"] = {"classifierMinConfidence": 0.6}
        if "BROWSER_IDEMPOTENT_REPLAY" in message:
            idempotency_key = "browser-stable-idempotency"
        return super().handle_command(
            session_id,
            message,
            idempotency_key=idempotency_key,
            **kwargs,
        )


def browser_runtime_service(
    session: Session = Depends(get_session),
) -> RuntimeLabService:
    return BrowserRuntimeLabService(
        RuntimeLabRepository(session),
        classifier=BrowserFixtureClassifier(),
        policy_thresholds={"classifierMinConfidence": 0.6},
    )


app.dependency_overrides[get_runtime_lab_service] = browser_runtime_service
