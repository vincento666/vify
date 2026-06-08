import json
from json import JSONDecodeError
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.database import get_session
from app.core.responses import success
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.runtime_lab.domain.classifier import LlmConstrainedIntentClassifier
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.runtime_lab.domain.chatflow_adapter import ChatflowSopRuntimeAdapter
from app.modules.runtime_lab.domain.faq_gate import FaqExactAnswerGate
from app.modules.runtime_lab.domain.payload import format_event, format_session, format_task
from app.modules.runtime_lab.domain.service import RuntimeLabService
from app.modules.runtime_lab.domain.sop_adapter import FakeSopRuntimeAdapter
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository
from app.modules.runtime_lab.web.schemas import RuntimeLabMessageRequest
from app.modules.workflow.domain.service import WorkflowService
from app.modules.workflow.infra.chatflow_state_repository import ChatflowStateRepository
from app.modules.workflow.infra.repository import WorkflowRepository

router = APIRouter(prefix="/api/v1/runtime-lab", tags=["runtime-lab"])


def get_runtime_lab_service(session: Session = Depends(get_session)) -> RuntimeLabService:
    settings = get_settings()
    bindings = _runtime_lab_chatflow_bindings(settings.runtime_lab_sop_chatflow_ids)
    classifier = _runtime_lab_intent_classifier(settings)
    faq_answer_gate = _runtime_lab_faq_answer_gate(settings, session)
    if not bindings:
        return RuntimeLabService(RuntimeLabRepository(session), classifier=classifier, faq_answer_gate=faq_answer_gate)
    workflow_service = WorkflowService(
        WorkflowRepository(session),
        flow_type="CHATFLOW",
        chatflow_state_repository=ChatflowStateRepository(session),
    )
    adapter = ChatflowSopRuntimeAdapter(
        workflow_service,
        sop_chatflow_ids=bindings,
        fallback_adapter=FakeSopRuntimeAdapter(),
    )
    return RuntimeLabService(
        RuntimeLabRepository(session),
        adapter=adapter,
        classifier=classifier,
        faq_answer_gate=faq_answer_gate,
    )


@router.post("/sessions")
def create_session(service: RuntimeLabService = Depends(get_runtime_lab_service)) -> dict[str, Any]:
    return success(format_session(service.create_session()))


@router.post("/sessions/{session_id}/messages")
def post_message(
    session_id: int,
    request: RuntimeLabMessageRequest,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    result = service.handle_command(
        session_id,
        request.message,
        request.idempotency_key,
        enabled_sop_ids=request.enabled_sop_ids,
    )
    return success(result.payload)


@router.get("/sessions/{session_id}/tasks")
def list_tasks(
    session_id: int,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    tasks = service.list_tasks(session_id)
    return success({"list": [format_task(task) for task in tasks], "total": len(tasks)})


@router.get("/sessions/{session_id}/events")
def list_events(
    session_id: int,
    service: RuntimeLabService = Depends(get_runtime_lab_service),
) -> dict[str, Any]:
    events = service.list_events(session_id)
    return success({"list": [format_event(event) for event in events], "total": len(events)})


def _runtime_lab_chatflow_bindings(raw: str | None) -> dict[str, int]:
    text = (raw or "").strip()
    if not text:
        return {}
    if text.startswith("{"):
        try:
            parsed = json.loads(text)
        except JSONDecodeError:
            return _runtime_lab_chatflow_bindings(text.strip("{}"))
        if not isinstance(parsed, dict):
            return {}
        return {str(key): int(value) for key, value in parsed.items() if str(key).strip()}
    bindings: dict[str, int] = {}
    for item in text.split(","):
        sop_id, _, chatflow_id = item.partition(":")
        if sop_id.strip() and chatflow_id.strip():
            bindings[sop_id.strip()] = int(chatflow_id.strip())
    return bindings


def _runtime_lab_faq_answer_gate(settings: Settings, session: Session) -> FaqExactAnswerGate | None:
    knowledge_base_ids = _runtime_lab_id_list(settings.runtime_lab_faq_knowledge_base_ids)
    if not knowledge_base_ids:
        return None
    return FaqExactAnswerGate(KnowledgeFacade(session), knowledge_base_ids=knowledge_base_ids)


def _runtime_lab_id_list(raw: str | None) -> list[int]:
    text = (raw or "").strip()
    if not text:
        return []
    ids: list[int] = []
    for item in text.split(","):
        item = item.strip()
        if not item:
            continue
        try:
            ids.append(int(item))
        except ValueError:
            continue
    return ids


def _runtime_lab_intent_classifier(settings: Settings) -> LlmConstrainedIntentClassifier | None:
    mode = settings.runtime_lab_intent_arbitrator_mode.strip().lower()
    if mode != "llm":
        return None
    base_url = (settings.runtime_lab_intent_arbitrator_base_url or "").strip()
    model = settings.runtime_lab_intent_arbitrator_model.strip()
    api_key = (settings.runtime_lab_intent_arbitrator_api_key or "").strip()
    if not base_url or not model:
        return None
    if not api_key and not base_url.startswith("mock://"):
        return None
    client = ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type="OPENAI_COMPATIBLE",
            base_url=base_url,
            auth_config={"api_key": api_key},
        ),
        timeout=20.0,
        max_attempts=1,
    )
    builder = OpenAIChatRequestBuilder()

    def complete(classifier_payload: dict[str, Any]) -> dict[str, Any]:
        llm_payload = builder.build(
            model=model,
            messages=[
                ChatRequestMessage(
                    role="system",
                    content=(
                        "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择，"
                        "返回 JSON 对象：selected_action, selected_candidate_id, confidence, rationale, "
                        "needs_clarification, clarification_question。不要创造候选。"
                    ),
                ),
                ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
            ],
            temperature=0.0,
            max_tokens=400,
            extra_params={"response_format": {"type": "json_object"}},
        )
        return _parse_llm_classifier_response(client.complete(llm_payload))

    return LlmConstrainedIntentClassifier(complete)


def _parse_llm_classifier_response(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("LLM classifier response has no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str):
        raise RuntimeError("LLM classifier response has no text content")
    try:
        parsed = json.loads(content)
    except JSONDecodeError:
        parsed = json.loads(_extract_json_object(content))
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM classifier response JSON is not an object")
    return parsed


def _extract_json_object(text: str) -> str:
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        raise JSONDecodeError("No JSON object found", text, 0)
    return text[start : end + 1]
