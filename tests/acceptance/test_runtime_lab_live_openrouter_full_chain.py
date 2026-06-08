from __future__ import annotations

from collections.abc import Callable
import json
import os
from pathlib import Path
import time
import unittest
from typing import Any, cast

from fastapi import Depends
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.database import get_session, initialise_database
from app.core.schema import register_baseline_tables
from app.main import app
from app.modules.agent.infra.repository import AgentRepository
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.runtime_lab.domain.classifier import ClassifierInput, ClassifierResult, LlmConstrainedIntentClassifier
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.router import _parse_llm_classifier_response, get_runtime_lab_service
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository
from tests.acceptance.test_runtime_lab_live_chatflow_llm_sop import (
    LiveSopCase,
    _assert_active,
    _case,
    _create_live_chatflow_sop,
    _message,
    _seed_default_live_agent,
)
from tests.acceptance.test_runtime_lab_openrouter_free_arbitrator import (
    FALLBACK_MODEL,
)

RUN_LIVE = os.getenv("HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FULL_CHAIN") == "1"
ARTIFACT_PATH = Path(
    "artifacts/slices/034-unified-routing-chat-lab/034.11/live-openrouter-full-chain.md"
)
DEFAULT_ARBITRATOR_MODEL = "qwen/qwen3.5-9b"
DEFAULT_HIGH_INTELLIGENCE_MODEL = "deepseek/deepseek-v4-flash"


@unittest.skipUnless(
    RUN_LIVE,
    "Set HIFY_RUN_LIVE_RUNTIME_LAB_OPENROUTER_FULL_CHAIN=1 and OPENROUTER_API_KEY to run live full-chain acceptance",
)
class RuntimeLabLiveOpenRouterFullChainAcceptanceTest(unittest.TestCase):
    def setUp(self) -> None:
        self.api_key = os.environ["OPENROUTER_API_KEY"]
        self.base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").rstrip("/")
        self.arbitrator_model = os.getenv("HIFY_OPENROUTER_ARBITRATOR_MODEL", DEFAULT_ARBITRATOR_MODEL)
        self.high_intelligence_model = os.getenv(
            "HIFY_OPENROUTER_HIGH_INTELLIGENCE_MODEL",
            DEFAULT_HIGH_INTELLIGENCE_MODEL,
        )
        self.sop_model = os.getenv("OPENROUTER_MODEL", self.arbitrator_model or FALLBACK_MODEL)
        initialise_database()
        register_baseline_tables()
        _seed_default_live_agent(self.api_key, self.base_url, self.sop_model)

    def test_live_openrouter_arbitrates_switch_and_executes_chatflow_llm_nodes(self) -> None:
        classifier = _live_single_model_classifier(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.arbitrator_model,
        )
        primary = _case("refund_ticket")
        secondary = _case("invoice_apply")
        stamp = time.time_ns()

        with TestClient(app) as client:
            bindings = _create_bindings(client, (primary, secondary), stamp)
            app.dependency_overrides[get_runtime_lab_service] = _runtime_service_override(bindings, classifier)
            try:
                session_id = client.post("/api/v1/runtime-lab/sessions").json()["data"]["id"]

                started = _message(client, session_id, primary.start_message)
                _assert_active(started, "START_SOP", primary.sop_id, "info_order")

                switched = _message(client, session_id, secondary.start_message)
                _assert_active(switched, "SUSPEND_AND_START", secondary.sop_id, "info_order")
                _assert_live_arbitrator(switched)

                _message(client, session_id, f"手机号 {secondary.phone}")
                secondary_completed = _message(client, session_id, "确认")
                _assert_live_sop_llm_reply(secondary_completed, secondary.marker)

                resumed = _message(client, session_id, primary.resume_message)
                _assert_active(resumed, "RESUME_TASK", primary.sop_id, "info_order")

                _message(client, session_id, f"手机号 {primary.phone}")
                primary_completed = _message(client, session_id, "确认")
                _assert_live_sop_llm_reply(primary_completed, primary.marker)
            finally:
                app.dependency_overrides.pop(get_runtime_lab_service, None)

        _write_artifact(
            base_url=self.base_url,
            arbitrator_model=self.arbitrator_model,
            high_intelligence_model=self.high_intelligence_model,
            sop_model=self.sop_model,
            classifier=classifier,
            switched=switched,
            completions=[secondary_completed, primary_completed],
        )


def _runtime_service_override(
    bindings: dict[str, int],
    classifier: "_SingleOpenRouterModelClassifier",
) -> Callable[[Session], RuntimeLabService]:
    def override(session: Session = Depends(get_session)) -> RuntimeLabService:
        workflow_service = WorkflowService(
            WorkflowRepository(session),
            flow_type="CHATFLOW",
            agent_repository=AgentRepository(session),
            model_facade=ProviderModelFacade(session),
            chatflow_state_repository=ChatflowStateRepository(session),
        )
        adapter = ChatflowSopRuntimeAdapter(workflow_service, sop_chatflow_ids=bindings)
        return RuntimeLabService(RuntimeLabRepository(session), adapter=adapter, classifier=classifier)

    return override


class _SingleOpenRouterModelClassifier:
    def __init__(self, *, model: str, complete: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self.model = model
        self._complete = complete
        self.attempts: list[dict[str, str]] = []
        self.success_model: str | None = None

    def classify(self, classifier_input: ClassifierInput) -> ClassifierResult:
        try:
            result = LlmConstrainedIntentClassifier(self._complete).classify(classifier_input)
        except Exception as exc:  # noqa: BLE001 - live gate records provider/model failures as acceptance evidence.
            self.attempts.append({"model": self.model, "status": "failed", "error": str(exc)[:300]})
            raise
        self.success_model = self.model
        self.attempts.append({"model": self.model, "status": "passed", "error": ""})
        return result


def _live_single_model_classifier(
    *,
    base_url: str,
    api_key: str,
    model: str,
    timeout: float = 30.0,
    max_attempts: int = 1,
    retry_sleep: float = 0.5,
) -> _SingleOpenRouterModelClassifier:
    builder = OpenAIChatRequestBuilder()
    client = ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type="OPENAI_COMPATIBLE",
            base_url=base_url,
            auth_config={"api_key": api_key},
        ),
        timeout=timeout,
        max_attempts=max_attempts,
        retry_sleep=retry_sleep,
    )

    def complete(classifier_payload: dict[str, Any]) -> dict[str, Any]:
        payload = builder.build(
            model=model,
            messages=[
                ChatRequestMessage(
                    role="system",
                    content=(
                        "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择。"
                        "返回 JSON 对象，字段必须是 selected_action, selected_candidate_id, confidence, "
                        "rationale, needs_clarification, clarification_question。不要创造候选。"
                        "当用户明确请求新业务且候选中存在 SOP_INTENT 时，应优先选择该 SOP_INTENT。"
                    ),
                ),
                ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
            ],
            temperature=0.0,
            max_tokens=1200,
            extra_params={
                "response_format": {"type": "json_object"},
                "reasoning": {"effort": "none", "exclude": True},
            },
        )
        return _parse_llm_classifier_response(client.complete(payload))

    return _SingleOpenRouterModelClassifier(model=model, complete=complete)


def _create_bindings(client: TestClient, cases: tuple[LiveSopCase, ...], stamp: int) -> dict[str, int]:
    return {
        case.sop_id: int(cast(int | str, _create_live_chatflow_sop(client, case, stamp)["id"]))
        for case in cases
    }


def _assert_live_arbitrator(actual: dict[str, Any]) -> None:
    decision = actual["routeDecision"]
    assert decision["policyGate"]["stage"] == "post_classifier"
    classifier_result = decision["classifierResult"]
    assert classifier_result["arbitrator_mode"] == "llm"
    assert classifier_result["used_real_llm"] is True


def _assert_live_sop_llm_reply(actual: dict[str, Any], marker: str) -> None:
    reply = str(actual.get("reply") or "")
    assert actual["routeDecision"]["action"] == "COMPLETE_TASK"
    assert marker in reply
    assert "LLM mock:" not in reply
    assert "Workflow mock:" not in reply
    assert "RAG mock:" not in reply


def _write_artifact(
    *,
    base_url: str,
    arbitrator_model: str,
    high_intelligence_model: str,
    sop_model: str,
    classifier: _SingleOpenRouterModelClassifier,
    switched: dict[str, Any],
    completions: list[dict[str, Any]],
) -> None:
    ARTIFACT_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# RuntimeLab Live OpenRouter Full Chain Acceptance",
        "",
        "- Slice: 034.11 live full-chain gate",
        "- Entry: `/api/v1/runtime-lab/sessions/{id}/messages`",
        "- Intent arbitrator: live OpenRouter single target model",
        "- SOP execution: live provider-backed Chatflow `LLM` nodes",
        f"- Base URL: `{base_url}`",
        f"- Target arbitrator model: `{arbitrator_model}`",
        f"- High-intelligence optional model: `{high_intelligence_model}`",
        f"- Arbitrator success model: `{classifier.success_model}`",
        f"- Chatflow SOP LLM model: `{sop_model}`",
        "- API key: runtime environment only, not recorded",
        f"- Switch action: `{switched['routeDecision']['action']}`",
        f"- Switch classifier mode: `{switched['routeDecision']['classifierResult']['arbitrator_mode']}`",
        "",
        "## Arbitrator Attempts",
        "",
    ]
    for attempt in classifier.attempts:
        lines.append(f"- `{attempt['model']}`: {attempt['status']} {attempt.get('error', '')}".rstrip())
    lines.extend(["", "## Live SOP LLM Replies", ""])
    for item in completions:
        lines.append(f"- `{item['routeDecision']['action']}`: {str(item.get('reply') or '')[:240]}")
    lines.append("")
    ARTIFACT_PATH.write_text("\n".join(lines), encoding="utf-8")
