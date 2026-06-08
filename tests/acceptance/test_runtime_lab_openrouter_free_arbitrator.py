from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import replace
import json
import os
from pathlib import Path
import unittest
from typing import Any

from fastapi import Depends
from fastapi.testclient import TestClient
import httpx
from sqlalchemy.orm import Session

from app.core.database import get_session, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.runtime_lab.domain.classifier import (
    ClassifierInput,
    ClassifierResult,
    LlmConstrainedIntentClassifier,
)
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import _parse_llm_classifier_response, get_runtime_lab_service


RUN_LIVE = os.getenv("HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FREE_ARBITRATOR") == "1"
ARTIFACT_PATH = Path(
    "artifacts/slices/034-unified-routing-chat-lab/034.10/openrouter-free-arbitrator.md"
)
FALLBACK_MODEL = "xiaomi/mimo-v2-flash"


class OpenRouterFreeArbitratorHarnessTest(unittest.TestCase):
    def test_free_text_filter_keeps_zero_priced_text_output_models(self) -> None:
        payload = {
            "data": [
                {
                    "id": "free/text:free",
                    "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                    "pricing": {"prompt": "0", "completion": "0"},
                },
                {
                    "id": "paid/text",
                    "architecture": {"input_modalities": ["text"], "output_modalities": ["text"]},
                    "pricing": {"prompt": "0.1", "completion": "0"},
                },
                {
                    "id": "free/image-out:free",
                    "architecture": {"input_modalities": ["text"], "output_modalities": ["image"]},
                    "pricing": {"prompt": "0", "completion": "0"},
                },
                {
                    "id": "free/multimodal-text:free",
                    "architecture": {"input_modalities": ["text", "image"], "output_modalities": ["text"]},
                    "pricing": {"prompt": "0", "completion": "0"},
                },
            ]
        }

        self.assertEqual(
            _openrouter_free_text_model_ids(payload),
            ("free/text:free", "free/multimodal-text:free"),
        )

    def test_test_stage_pool_tries_free_models_then_single_fallback(self) -> None:
        attempts: list[dict[str, str]] = []

        def complete(model: str, _payload: dict[str, Any]) -> dict[str, Any]:
            attempts.append({"model": model, "status": "called"})
            if model != FALLBACK_MODEL:
                raise RuntimeError("free quota exhausted")
            return {
                "selected_action": "START_SOP",
                "selected_candidate_id": "sop:flight_status",
                "confidence": 0.92,
                "rationale": "fallback selected finite candidate",
                "needs_clarification": False,
                "clarification_question": None,
            }

        classifier = _TestStageOpenRouterFreeModelPoolClassifier(
            free_model_ids=("free/a:free", "free/b:free"),
            fallback_model=FALLBACK_MODEL,
            complete=complete,
        )

        result = classifier.classify(_classifier_input())

        self.assertEqual([item["model"] for item in attempts], ["free/a:free", "free/b:free", FALLBACK_MODEL])
        self.assertEqual(result.selected_action, "START_SOP")
        self.assertEqual(result.selected_candidate_id, "sop:flight_status")
        self.assertEqual(result.arbitrator_mode, "llm")
        self.assertTrue(result.used_real_llm)
        self.assertIn(FALLBACK_MODEL, result.rationale)


@unittest.skipUnless(
    RUN_LIVE,
    "Set HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FREE_ARBITRATOR=1 and OPENROUTER_API_KEY to run live 034.10",
)
class RuntimeLabOpenRouterFreeArbitratorAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.fallback_model = os.getenv("HIFY_OPENROUTER_FALLBACK_MODEL", FALLBACK_MODEL)
        initialise_database()
        register_baseline_tables()

    def test_free_model_pool_arbitrates_runtime_lab_switch_with_xiaomi_fallback(self) -> None:
        discovered_models = _discover_free_text_models(self.base_url)
        classifier = _live_pool_classifier(
            base_url=self.base_url,
            api_key=self.api_key,
            free_model_ids=discovered_models,
            fallback_model=self.fallback_model,
        )
        with TestClient(app) as client:
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(classifier)
            try:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]
                started = _message(client, session_id, "我要退票")
                switched = _message(client, session_id, "我想查一下今天航班动态，听说天气不好")
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        self.assertEqual(started["routeDecision"]["action"], "START_SOP")
        self.assertEqual(switched["routeDecision"]["action"], "SUSPEND_AND_START")
        self.assertEqual(switched["activeTask"]["sopId"], "flight_status")
        classifier_result = switched["routeDecision"]["classifierResult"]
        self.assertEqual(classifier_result["arbitrator_mode"], "llm")
        self.assertTrue(classifier_result["used_real_llm"])
        self.assertTrue(classifier.success_model)
        _write_artifact(self.base_url, discovered_models, classifier, switched)


class _TestStageOpenRouterFreeModelPoolClassifier:
    def __init__(
        self,
        *,
        free_model_ids: Sequence[str],
        fallback_model: str,
        complete: Callable[[str, dict[str, Any]], dict[str, Any]],
        accept_result: Callable[[ClassifierInput, ClassifierResult], bool] | None = None,
    ) -> None:
        self.free_model_ids = tuple(free_model_ids)
        self.fallback_model = fallback_model
        self._complete = complete
        self._accept_result = accept_result
        self.attempts: list[dict[str, str]] = []
        self.success_model: str | None = None

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        last_error = "no model attempted"
        for model in _ordered_models(self.free_model_ids, self.fallback_model):
            try:
                classifier = LlmConstrainedIntentClassifier(
                    lambda payload, selected_model=model: self._complete(selected_model, payload)
                )
                result = classifier.classify(classifier_input)
                if self._accept_result is not None and not self._accept_result(classifier_input, result):
                    raise RuntimeError("valid finite decision rejected by 034.10 runtime switch expectation")
            except Exception as exc:  # noqa: BLE001 - live model pool must skip provider/format/quota failures.
                last_error = str(exc)
                self.attempts.append({"model": model, "status": "failed", "error": last_error[:300]})
                continue
            self.success_model = model
            self.attempts.append({"model": model, "status": "passed", "error": ""})
            return replace(result, rationale=f"{result.rationale} | model={model}")
        raise RuntimeError(f"No OpenRouter free/fallback model produced a valid finite decision: {last_error}")


def _live_pool_classifier(
    *,
    base_url: str,
    api_key: str,
    free_model_ids: Sequence[str],
    fallback_model: str,
) -> _TestStageOpenRouterFreeModelPoolClassifier:
    builder = OpenAIChatRequestBuilder()
    client = ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type="OPENAI_COMPATIBLE",
            base_url=base_url,
            auth_config={"api_key": api_key},
        ),
        timeout=20.0,
        max_attempts=1,
    )

    def complete(model: str, classifier_payload: dict[str, Any]) -> dict[str, Any]:
        errors: list[str] = []
        for json_mode in (True, False):
            extra_params = {"response_format": {"type": "json_object"}} if json_mode else {}
            llm_payload = builder.build(
                model=model,
                messages=[
                    ChatRequestMessage(
                        role="system",
                        content=(
                            "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择。"
                            "返回 JSON 对象，字段必须是 selected_action, selected_candidate_id, confidence, "
                            "rationale, needs_clarification, clarification_question。不要创造候选。"
                        ),
                    ),
                    ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
                ],
                temperature=0.0,
                max_tokens=400,
                extra_params=extra_params,
            )
            try:
                return _parse_llm_classifier_response(client.complete(llm_payload))
            except Exception as exc:  # noqa: BLE001 - second attempt intentionally relaxes json mode.
                errors.append(str(exc))
        raise RuntimeError(" | ".join(errors))

    return _TestStageOpenRouterFreeModelPoolClassifier(
        free_model_ids=free_model_ids,
        fallback_model=fallback_model,
        complete=complete,
        accept_result=_accept_strong_sop_switch,
    )


def _accept_strong_sop_switch(classifier_input: ClassifierInput, result: ClassifierResult) -> bool:
    if not classifier_input.session_state.get("activeTask"):
        return True
    strong_sop_candidate_ids = {
        candidate.candidate_id
        for candidate in classifier_input.candidates
        if str(candidate.candidate_type) == "SOP_INTENT" and candidate.score >= 0.9
    }
    if not strong_sop_candidate_ids:
        return True
    return result.selected_candidate_id in strong_sop_candidate_ids


def _discover_free_text_models(base_url: str) -> tuple[str, ...]:
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.get(f"{base_url.rstrip('/')}/models")
    if response.status_code >= 400:
        raise AssertionError(f"OpenRouter models discovery failed: {response.status_code} {response.text}")
    discovered = _openrouter_free_text_model_ids(response.json())
    raw_limit = os.getenv("HIFY_OPENROUTER_FREE_MODEL_LIMIT", "").strip()
    limit = int(raw_limit) if raw_limit.isdigit() else 0
    return discovered[:limit] if limit > 0 else discovered


def _openrouter_free_text_model_ids(payload: dict[str, Any]) -> tuple[str, ...]:
    models = payload.get("data")
    if not isinstance(models, list):
        return ()
    ids: list[str] = []
    for item in models:
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        architecture = item.get("architecture") if isinstance(item.get("architecture"), dict) else {}
        input_modalities = architecture.get("input_modalities")
        output_modalities = architecture.get("output_modalities")
        pricing = item.get("pricing") if isinstance(item.get("pricing"), dict) else {}
        if (
            model_id
            and _contains_text(input_modalities)
            and _contains_text(output_modalities)
            and _zero_price(pricing.get("prompt"))
            and _zero_price(pricing.get("completion"))
        ):
            ids.append(model_id)
    return tuple(dict.fromkeys(ids))


def _contains_text(value: object) -> bool:
    return isinstance(value, list) and "text" in {str(item) for item in value}


def _zero_price(value: object) -> bool:
    try:
        return float(str(value)) == 0.0
    except ValueError:
        return False


def _ordered_models(free_model_ids: Sequence[str], fallback_model: str) -> tuple[str, ...]:
    seen: set[str] = set()
    ordered: list[str] = []
    for model in (*free_model_ids, fallback_model):
        model_id = str(model).strip()
        if model_id and model_id not in seen:
            seen.add(model_id)
            ordered.append(model_id)
    return tuple(ordered)


def _runtime_service_override(classifier: Any) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        return RuntimeLabService(RuntimeLabRepository(session), classifier=classifier)

    return override


def _message(client: TestClient, session_id: int, message: str) -> dict[str, Any]:
    response = client.post(f"/api/v1/runtime-lab/sessions/{session_id}/messages", json={"message": message})
    assert response.status_code == 200, response.text
    data = response.json()["data"]
    assert isinstance(data, dict)
    return data


def _classifier_input() -> ClassifierInput:
    from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown

    return ClassifierInput(
        message="我想查一下今天航班动态，听说天气不好",
        session_state={"activeTask": True, "suspendedTaskCount": 0},
        candidates=(
            RouteCandidate(
                candidate_id="active:1",
                candidate_type=CandidateType.ACTIVE_TASK_CONTINUE,
                target_id="1",
                display_name="Continue refund_ticket",
                source="mock_semantic_recall",
                score=0.55,
                score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=0.55),
                matched_terms=(),
                risk_level="LOW",
                requires_classifier=True,
                reason="active task",
            ),
            RouteCandidate(
                candidate_id="sop:flight_status",
                candidate_type=CandidateType.SOP_INTENT,
                target_id="flight_status",
                display_name="航班动态",
                source="explicit_signal",
                score=1.0,
                score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
                matched_terms=("航班动态",),
                risk_level="LOW",
                requires_classifier=True,
                reason="new SOP",
            ),
        ),
        allowed_actions=("CONTINUE_ACTIVE_SOP", "START_SOP", "SUSPEND_AND_START", "CLARIFY"),
        thresholds={"classifierMinConfidence": 0.6},
    )


def _write_artifact(
    base_url: str,
    discovered_models: Sequence[str],
    classifier: _TestStageOpenRouterFreeModelPoolClassifier,
    switched: dict[str, Any],
) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Runtime Lab OpenRouter Free Arbitrator Acceptance",
        "",
        "- Slice: 034.10 test-stage live LLM arbitrator",
        f"- Base URL: `{base_url}`",
        f"- Discovered free text models: {len(discovered_models)}",
        f"- Fallback model: `{classifier.fallback_model}`",
        f"- Success model: `{classifier.success_model}`",
        "- Production runtime-lab factory changed: no",
        f"- Final action: `{switched['routeDecision']['action']}`",
        f"- Active SOP: `{switched['activeTask']['sopId']}`",
        "",
        "## Attempted Models",
        "",
    ]
    for attempt in classifier.attempts:
        lines.append(f"- `{attempt['model']}`: {attempt['status']} {attempt.get('error', '')}".rstrip())
    lines.extend(["", "## Discovered Model Snapshot", ""])
    for model_id in discovered_models:
        lines.append(f"- `{model_id}`")
    lines.append("")
    ARTIFACT_PATH.write_text("\n".join(lines), encoding="utf-8")
