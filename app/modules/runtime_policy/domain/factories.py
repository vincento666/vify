import json
from time import perf_counter
from typing import Any

from app.core.config import Settings
from app.modules.chat.domain.service import ChatService
from app.modules.chat.infra.repository import ChatRepository
from app.modules.chat.web.schemas import ChatMessageCreateRequest, ChatSessionCreateRequest
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.runtime_lab.domain.agent_fallback import (
    AgentOutputPolicy,
    FakeFallbackAgent,
    FallbackAgentOutput,
    FallbackAgentPort,
    FallbackAgentRequest,
)
from app.modules.runtime_lab.domain.classifier import LlmConstrainedIntentClassifier
from app.modules.workflow.api.facade import WorkflowFacade
from sqlalchemy.orm import Session

DEFAULT_CLASSIFIER_PROMPT = (
    "你是民航客服路由仲裁器。只能从用户给定的 candidates 和 allowedActions 中选择，"
    "返回 JSON 对象：selected_action, selected_candidate_id, confidence, rationale, "
    "needs_clarification, clarification_question。不要创造候选。"
)


def build_classifier_from_snapshot(snapshot: dict[str, Any], _settings: Settings) -> Any | None:
    classifier = snapshot.get("classifier")
    if not isinstance(classifier, dict):
        return None
    if not bool(classifier.get("enabled")) or str(classifier.get("mode") or "fake").lower() != "llm":
        return None
    base_url = str(classifier.get("baseUrl") or "").strip()
    model = str(classifier.get("model") or "").strip()
    if not base_url or not model:
        return None
    fallback_model = str(classifier.get("fallbackModel") or "").strip()
    prompt_template = str(classifier.get("promptTemplate") or "").strip() or DEFAULT_CLASSIFIER_PROMPT
    temperature = float(classifier.get("temperature") or 0.0)
    max_tokens = int(classifier.get("maxTokens") or 360)
    response_format = str(classifier.get("responseFormat") or "json").strip().lower()
    client = ProviderBackedOpenAIChatClient(
        ProviderChatConfig(
            provider_type=str(classifier.get("providerType") or "OPENAI_COMPATIBLE"),
            base_url=base_url,
            auth_config={
                "api_key": "",
                "api_key_ref": str(classifier.get("apiKeyRef") or ""),
            },
        ),
        timeout=float(classifier.get("timeoutSeconds") or 90.0),
        max_attempts=int(classifier.get("maxAttempts") or 3),
        retry_sleep=float(classifier.get("retrySleepSeconds") or 2.0),
    )
    builder = OpenAIChatRequestBuilder()

    def complete(classifier_payload: dict[str, Any]) -> dict[str, Any]:
        llm_payload = builder.build(
            model=model,
            messages=[
                ChatRequestMessage(role="system", content=prompt_template),
                ChatRequestMessage(role="user", content=json.dumps(classifier_payload, ensure_ascii=False)),
            ],
            temperature=temperature,
            max_tokens=max_tokens,
            extra_params=_classifier_extra_params(response_format),
        )
        started_at = perf_counter()
        actual_model = model
        try:
            response = client.complete(llm_payload)
        except Exception:
            if not fallback_model or fallback_model == model:
                raise
            fallback_payload = dict(llm_payload)
            fallback_payload["model"] = fallback_model
            actual_model = fallback_model
            response = client.complete(fallback_payload)
        parsed = _parse_classifier_response(response)
        parsed_output = dict(parsed)
        parsed["_debug"] = {
            "model": actual_model,
            "elapsedMs": int((perf_counter() - started_at) * 1000),
            "input": _redact_llm_payload(llm_payload),
            "output": parsed_output,
            "usage": _usage_from_response(response, llm_payload, parsed_output),
            "source": "runtime_policy_profile",
            "profileId": snapshot.get("profileId"),
            "profileVersion": snapshot.get("profileVersion"),
        }
        return parsed

    return LlmConstrainedIntentClassifier(complete)


def build_fallback_agent_from_snapshot(
    snapshot: dict[str, Any],
    *,
    session: Session | None = None,
) -> FallbackAgentPort | None:
    fallback_agent = snapshot.get("fallbackAgent")
    if not isinstance(fallback_agent, dict):
        return FakeFallbackAgent()
    if not bool(fallback_agent.get("enabled")):
        return None
    if str(fallback_agent.get("type") or "fake") == "fake":
        return FakeFallbackAgent()
    if str(fallback_agent.get("type") or "") == "existing_agent":
        agent_id = _optional_int(fallback_agent.get("agentId"))
        if session is None or agent_id is None:
            return None
        return ExistingAgentFallbackAgent(session, agent_id)
    return None


class ExistingAgentFallbackAgent:
    def __init__(self, session: Session, agent_id: int) -> None:
        self._session = session
        self._agent_id = agent_id

    def run(self, request: FallbackAgentRequest) -> FallbackAgentOutput:
        started_at = perf_counter()
        try:
            chat_service = ChatService(
                ChatRepository(self._session),
                knowledge_facade=KnowledgeFacade(self._session),
                workflow_facade=WorkflowFacade(self._session),
                mcp_facade=McpFacade(self._session),
                model_facade=ProviderModelFacade(self._session),
            )
            chat_session = chat_service.create_session(ChatSessionCreateRequest(agentId=self._agent_id))
            turn = chat_service.send_message(
                int(chat_session["id"]),
                ChatMessageCreateRequest(
                    content=request.message,
                    stream=False,
                    variables={},
                ),
            )
        except Exception as exc:
            return FallbackAgentOutput(
                response_type="clarification",
                clarification_question="兜底智能体暂时不可用，请补充问题背景或稍后重试。",
                confidence=0.35,
                safety_flags=[f"fallback_agent_error:{type(exc).__name__}"],
            )
        assistant = dict(turn.get("assistantMessage") or {})
        answer = str(assistant.get("content") or "").strip()
        if not answer:
            return FallbackAgentOutput(
                response_type="clarification",
                clarification_question="兜底智能体未生成有效回复，请补充问题背景。",
                confidence=0.4,
                safety_flags=["fallback_agent_empty_answer"],
            )
        return FallbackAgentOutput(
            response_type="answer",
            answer=answer,
            confidence=0.72,
            citations=[
                {
                    "source": "agent",
                    "agentId": self._agent_id,
                    "sessionId": chat_session.get("id"),
                    "elapsedMs": int((perf_counter() - started_at) * 1000),
                    "runtimeContext": _fallback_agent_context(request),
                }
            ],
        )


def build_agent_output_policy_from_snapshot(snapshot: dict[str, Any]) -> AgentOutputPolicy:
    fallback_agent = snapshot.get("fallbackAgent")
    max_attempts = 2
    if isinstance(fallback_agent, dict):
        max_attempts = int(fallback_agent.get("maxClarificationAttempts") or 2)
    return AgentOutputPolicy(max_clarification_attempts=max_attempts)


def _classifier_extra_params(response_format: str) -> dict[str, Any]:
    if response_format == "json":
        return {
            "response_format": {"type": "json_object"},
            "reasoning": {"effort": "none", "exclude": True},
        }
    return {}


def _parse_classifier_response(response: dict[str, Any]) -> dict[str, Any]:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise RuntimeError("LLM classifier response has no choices")
    message = choices[0].get("message") if isinstance(choices[0], dict) else None
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, str) or not content.strip():
        raise RuntimeError("LLM classifier response has no content")
    parsed = json.loads(content)
    if not isinstance(parsed, dict):
        raise RuntimeError("LLM classifier response is not a JSON object")
    return parsed


def _redact_llm_payload(payload: dict[str, Any]) -> dict[str, Any]:
    redacted = dict(payload)
    redacted.pop("api_key", None)
    redacted.pop("apiKey", None)
    return redacted


def _usage_from_response(
    response: dict[str, Any],
    llm_payload: dict[str, Any],
    parsed_output: dict[str, Any],
) -> dict[str, Any]:
    usage = response.get("usage")
    if isinstance(usage, dict):
        input_tokens = _usage_int(usage, "inputTokens", "input_tokens", "prompt_tokens", "promptTokens")
        output_tokens = _usage_int(usage, "outputTokens", "output_tokens", "completion_tokens", "completionTokens")
        total_tokens = _usage_int(usage, "totalTokens", "total_tokens", "totalTokens")
        return {
            "inputTokens": input_tokens,
            "outputTokens": output_tokens,
            "totalTokens": total_tokens or input_tokens + output_tokens,
            "estimated": False,
        }
    input_tokens = _estimate_tokens(llm_payload)
    output_tokens = _estimate_tokens(parsed_output)
    return {
        "inputTokens": input_tokens,
        "outputTokens": output_tokens,
        "totalTokens": input_tokens + output_tokens,
        "estimated": True,
    }


def _usage_int(usage: dict[str, Any], *keys: str) -> int:
    for key in keys:
        try:
            value = int(usage.get(key))
        except (TypeError, ValueError):
            continue
        if value >= 0:
            return value
    return 0


def _estimate_tokens(payload: Any) -> int:
    text = json.dumps(payload, ensure_ascii=False, default=str)
    return max(1, len(text) // 4)


def _fallback_agent_context(request: FallbackAgentRequest) -> dict[str, Any]:
    context = {
        "activeTask": request.active_task,
        "suspendedTasks": request.suspended_tasks,
        "recentEvents": request.recent_events[-6:],
    }
    return json.loads(json.dumps(context, ensure_ascii=False, default=str))


def _optional_int(value: Any) -> int | None:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return None
    return parsed if parsed > 0 else None
