from dataclasses import dataclass
from typing import Any

from app.core.config import Settings
from app.modules.runtime_policy.infra.repository import RuntimePolicyRepository
from app.modules.runtime_policy.domain.service import _profile_response


@dataclass(frozen=True)
class RuntimePolicyResolveContext:
    tenant_id: str = ""
    bot_id: str = ""
    channel: str = ""
    session_id: str = ""
    sop_group: str = ""


class RuntimePolicyResolver:
    def __init__(self, repository: RuntimePolicyRepository, settings: Settings) -> None:
        self._repository = repository
        self._settings = settings

    def resolve(self, context: RuntimePolicyResolveContext | None = None) -> dict[str, Any]:
        context = context or RuntimePolicyResolveContext()
        profile = self._best_profile(context)
        if profile is None:
            return _env_effective_profile(self._settings)
        response = _profile_response(profile)
        return {
            "source": "profile",
            "profileId": response["id"],
            "profileVersion": response["version"],
            "policySnapshot": _profile_policy_snapshot(response),
        }

    def _best_profile(self, context: RuntimePolicyResolveContext) -> dict[str, Any] | None:
        candidates: list[tuple[int, dict[str, Any]]] = []
        for profile in self._repository.list_active_profiles():
            score = _binding_score(profile.get("bindings") or {}, context)
            if score is not None:
                candidates.append((score, profile))
        if not candidates:
            return None
        candidates.sort(key=lambda item: (item[0], int(item[1]["id"])), reverse=True)
        return candidates[0][1]


def _binding_score(bindings: dict[str, Any], context: RuntimePolicyResolveContext) -> int | None:
    score = 0
    for key, value in (
        ("tenantId", context.tenant_id),
        ("botId", context.bot_id),
        ("channel", context.channel),
        ("sessionId", context.session_id),
        ("sopGroup", context.sop_group),
    ):
        bound_value = str(bindings.get(key) or "").strip()
        context_value = str(value or "").strip()
        if not bound_value or not context_value:
            continue
        if bound_value != context_value:
            return None
        score += 1
    return score


def _profile_policy_snapshot(profile: dict[str, Any]) -> dict[str, Any]:
    return {
        "profileId": profile["id"],
        "profileVersion": profile["version"],
        "status": profile["status"],
        "mode": profile["mode"],
        "bindings": profile["bindings"],
        "thresholds": profile["thresholds"],
        "classifier": profile["classifier"],
        "faq": profile["faq"],
        "rag": profile["rag"],
        "fallbackAgent": profile["fallbackAgent"],
        "handoff": profile["handoff"],
    }


def _env_effective_profile(settings: Settings) -> dict[str, Any]:
    classifier_mode = settings.runtime_lab_intent_arbitrator_mode.strip().lower()
    base_url = (settings.runtime_lab_intent_arbitrator_base_url or "").strip()
    api_key_ref = "env:HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_API_KEY" if settings.runtime_lab_intent_arbitrator_api_key else ""
    return {
        "source": "env",
        "profileId": None,
        "profileVersion": None,
        "policySnapshot": {
            "profileId": None,
            "profileVersion": None,
            "status": "bootstrap",
            "mode": "balanced",
            "bindings": {
                "tenantId": "",
                "botId": "",
                "channel": "",
                "sessionId": "",
                "sopGroup": "",
            },
            "thresholds": {
                "strongAcceptThreshold": 0.9,
                "classifierMinConfidence": 0.6,
                "candidateTopK": 5,
                "candidateSourceWeights": {},
                "candidateMinMargin": 0.12,
                "llmArbitrationRequiredForNonHardStop": True,
                "faqKeywordMinScore": 0.0,
                "faqKeywordMinMargin": 0.0,
                "faqSemanticMinScore": 0.0,
                "faqSemanticMinMargin": 0.0,
                "ragMinScore": 0.0,
                "ragLexicalAcceptThreshold": 0.0,
            },
            "classifier": {
                "enabled": classifier_mode == "llm",
                "mode": classifier_mode,
                "providerType": "openai-compatible" if classifier_mode == "llm" else "fake",
                "baseUrl": base_url,
                "apiKeyRef": api_key_ref,
                "model": settings.runtime_lab_intent_arbitrator_model.strip(),
                "fallbackModel": (settings.runtime_lab_intent_arbitrator_fallback_model or "").strip(),
                "promptTemplate": "",
                "temperature": 0.0,
                "maxTokens": 360,
                "timeoutSeconds": 90.0,
                "maxAttempts": 3,
                "retrySleepSeconds": 2.0,
                "responseFormat": "json",
            },
            "faq": {
                "knowledgeBaseIds": _id_list(settings.runtime_lab_faq_knowledge_base_ids),
                "exactEnabled": True,
                "semanticEnabled": True,
                "topK": 3,
                "rerank": False,
            },
            "rag": {
                "enabled": bool(_id_list(settings.runtime_lab_rag_knowledge_base_ids)),
                "knowledgeBaseIds": _id_list(settings.runtime_lab_rag_knowledge_base_ids),
                "retrievalMode": "hybrid",
                "topK": 5,
                "rerank": True,
            },
            "fallbackAgent": {
                "enabled": True,
                "type": "fake",
                "agentId": None,
                "modelConfigId": None,
                "providerType": "mock",
                "baseUrl": "",
                "apiKeyRef": "",
                "model": "",
                "promptTemplate": "",
                "knowledgeBaseIds": [],
                "maxClarificationAttempts": 2,
                "allowedResponseTypes": ["answer", "clarify", "handoff"],
                "handoffRecommendationPolicy": "explicit_only",
            },
            "handoff": {
                "enabled": True,
                "triggerGroups": ["explicit_request"],
                "queue": "general",
                "escalationReasonMap": {},
            },
        },
    }


def _id_list(raw: str | None) -> list[int]:
    ids: list[int] = []
    for item in (raw or "").split(","):
        text = item.strip()
        if not text:
            continue
        try:
            ids.append(int(text))
        except ValueError:
            continue
    return ids
