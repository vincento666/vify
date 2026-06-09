from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RuntimePolicyBindings(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    tenant_id: str = Field(default="", alias="tenantId", max_length=120)
    bot_id: str = Field(default="", alias="botId", max_length=120)
    channel: str = Field(default="", max_length=80)
    session_id: str = Field(default="", alias="sessionId", max_length=120)
    sop_group: str = Field(default="", alias="sopGroup", max_length=120)


class RuntimePolicyThresholds(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    strong_accept_threshold: float = Field(alias="strongAcceptThreshold", ge=0, le=1)
    classifier_min_confidence: float = Field(alias="classifierMinConfidence", ge=0, le=1)
    faq_keyword_min_score: float = Field(alias="faqKeywordMinScore", ge=0, le=1)
    faq_keyword_min_margin: float = Field(alias="faqKeywordMinMargin", ge=0, le=1)
    faq_semantic_min_score: float = Field(alias="faqSemanticMinScore", ge=0, le=1)
    faq_semantic_min_margin: float = Field(alias="faqSemanticMinMargin", ge=0, le=1)
    rag_min_score: float = Field(alias="ragMinScore", ge=0, le=1)
    rag_lexical_accept_threshold: float = Field(alias="ragLexicalAcceptThreshold", ge=0, le=1)


class RuntimePolicyClassifier(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool
    mode: Literal["fake", "llm"]
    provider_type: str = Field(default="", alias="providerType", max_length=80)
    base_url: str = Field(default="", alias="baseUrl", max_length=500)
    api_key_ref: str = Field(default="", alias="apiKeyRef", max_length=240)
    model: str = Field(default="", max_length=160)
    fallback_model: str = Field(default="", alias="fallbackModel", max_length=160)
    prompt_template: str = Field(default="", alias="promptTemplate")
    temperature: float = Field(default=0.0, ge=0, le=2)
    max_tokens: int = Field(default=128, alias="maxTokens", ge=1, le=8192)
    timeout_seconds: float = Field(default=10.0, alias="timeoutSeconds", gt=0, le=120)
    max_attempts: int = Field(default=1, alias="maxAttempts", ge=1, le=5)
    retry_sleep_seconds: float = Field(default=0.0, alias="retrySleepSeconds", ge=0, le=30)
    response_format: str = Field(default="json", alias="responseFormat", max_length=40)

    @model_validator(mode="after")
    def validate_live_llm_config(self) -> Self:
        if self.enabled and self.mode == "llm":
            missing = [
                name
                for name, value in (
                    ("baseUrl", self.base_url),
                    ("apiKeyRef", self.api_key_ref),
                    ("model", self.model),
                )
                if not value.strip()
            ]
            if missing:
                raise ValueError(f"llm classifier requires {', '.join(missing)}")
        return self


class RuntimePolicyFaq(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    knowledge_base_ids: list[int] = Field(default_factory=list, alias="knowledgeBaseIds")
    exact_enabled: bool = Field(default=True, alias="exactEnabled")
    semantic_enabled: bool = Field(default=True, alias="semanticEnabled")
    top_k: int = Field(default=3, alias="topK", ge=1, le=50)
    rerank: bool = False


class RuntimePolicyRag(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = True
    knowledge_base_ids: list[int] = Field(default_factory=list, alias="knowledgeBaseIds")
    retrieval_mode: str = Field(default="hybrid", alias="retrievalMode", max_length=60)
    top_k: int = Field(default=5, alias="topK", ge=1, le=50)
    rerank: bool = False


class RuntimePolicyFallbackAgent(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = True
    type: Literal["fake", "llm_agent", "existing_agent", "external_webhook"]
    agent_id: int | None = Field(default=None, alias="agentId")
    model_config_id: int | None = Field(default=None, alias="modelConfigId")
    provider_type: str = Field(default="", alias="providerType", max_length=80)
    base_url: str = Field(default="", alias="baseUrl", max_length=500)
    api_key_ref: str = Field(default="", alias="apiKeyRef", max_length=240)
    model: str = Field(default="", max_length=160)
    prompt_template: str = Field(default="", alias="promptTemplate")
    knowledge_base_ids: list[int] = Field(default_factory=list, alias="knowledgeBaseIds")
    max_clarification_attempts: int = Field(default=2, alias="maxClarificationAttempts", ge=0, le=10)
    allowed_response_types: list[str] = Field(default_factory=list, alias="allowedResponseTypes")
    handoff_recommendation_policy: str = Field(
        default="explicit_only",
        alias="handoffRecommendationPolicy",
        max_length=80,
    )

    @model_validator(mode="after")
    def validate_fallback_shape(self) -> Self:
        if not self.enabled:
            return self
        if self.type == "existing_agent" and not self.agent_id:
            raise ValueError("existing_agent fallback requires agentId")
        if self.type == "llm_agent" and not self.model_config_id:
            missing = [
                name
                for name, value in (
                    ("providerType", self.provider_type),
                    ("baseUrl", self.base_url),
                    ("apiKeyRef", self.api_key_ref),
                    ("model", self.model),
                )
                if not value.strip()
            ]
            if missing:
                raise ValueError(f"llm_agent fallback requires modelConfigId or {', '.join(missing)}")
        if self.type == "external_webhook" and not self.base_url.strip():
            raise ValueError("external_webhook fallback requires baseUrl")
        return self


class RuntimePolicyHandoff(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    enabled: bool = True
    trigger_groups: list[str] = Field(default_factory=list, alias="triggerGroups")
    queue: str = Field(default="general", max_length=120)
    escalation_reason_map: dict[str, str] = Field(default_factory=dict, alias="escalationReasonMap")


class RuntimePolicyAudit(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    created_by: str = Field(default="system", alias="createdBy", max_length=120)
    updated_by: str = Field(default="system", alias="updatedBy", max_length=120)
    change_reason: str = Field(default="", alias="changeReason", max_length=500)


class RuntimePolicyProfileRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=500)
    status: Literal["draft", "active", "archived"] = "draft"
    mode: Literal["strict", "balanced", "recall_first", "custom"] = "balanced"
    bindings: RuntimePolicyBindings
    thresholds: RuntimePolicyThresholds
    classifier: RuntimePolicyClassifier
    faq: RuntimePolicyFaq
    rag: RuntimePolicyRag
    fallback_agent: RuntimePolicyFallbackAgent = Field(alias="fallbackAgent")
    handoff: RuntimePolicyHandoff
    audit: RuntimePolicyAudit


class RuntimePolicyProfileResponse(RuntimePolicyProfileRequest):
    id: int
    version: int
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class RuntimePolicyProfilePageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[RuntimePolicyProfileResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")
