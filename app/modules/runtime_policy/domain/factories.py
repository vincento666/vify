import json
from time import perf_counter
from typing import Any

from app.core.config import Settings
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.runtime_lab.domain.agent_fallback import AgentOutputPolicy, FakeFallbackAgent, FallbackAgentPort
from app.modules.runtime_lab.domain.classifier import LlmConstrainedIntentClassifier

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


def build_fallback_agent_from_snapshot(snapshot: dict[str, Any]) -> FallbackAgentPort | None:
    fallback_agent = snapshot.get("fallbackAgent")
    if not isinstance(fallback_agent, dict):
        return FakeFallbackAgent()
    if not bool(fallback_agent.get("enabled")):
        return None
    if str(fallback_agent.get("type") or "fake") == "fake":
        return FakeFallbackAgent()
    return None


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
        return dict(usage)
    return {
        "promptChars": len(json.dumps(llm_payload, ensure_ascii=False)),
        "completionChars": len(json.dumps(parsed_output, ensure_ascii=False)),
    }
