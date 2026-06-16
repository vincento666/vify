from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class EvalSetCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=500)


class EvalSetUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=500)


class EvalSetVersionCreateRequest(BaseModel):
    description: str = Field(default="", max_length=500)


class EvalSetFieldRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    key: str = Field(min_length=1, max_length=80)
    label: str = Field(min_length=1, max_length=120)
    content_type: str = Field(default="TEXT", alias="contentType")
    required: bool = False
    display_order: int = Field(default=0, alias="displayOrder")


class EvalSetFieldsUpdateRequest(BaseModel):
    fields: list[EvalSetFieldRequest] = Field(min_length=1)


class EvalCaseCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    input: str = Field(min_length=1)
    expected_output: str = Field(alias="expectedOutput", min_length=1)
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class EvalCaseUpdateRequest(EvalCaseCreateRequest):
    pass


class EvalCaseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    eval_set_id: int = Field(alias="evalSetId")
    input: str
    expected_output: str = Field(alias="expectedOutput")
    tags: list[str]
    metadata: dict[str, Any]
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class EvalCaseCsvImportResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    created_count: int = Field(alias="createdCount")


class EvalSetResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    description: str
    case_count: int = Field(alias="caseCount")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class EvalSetDetailResponse(EvalSetResponse):
    cases: list[EvalCaseResponse]


class EvalSetPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[EvalSetResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


EvaluatorType = Literal["EXACT_MATCH", "CONTAINS_KEYWORDS", "LLM_JUDGE"]


class EvaluatorCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    type: EvaluatorType
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluatorUpdateRequest(EvaluatorCreateRequest):
    enabled: int | None = None


class EvaluatorVersionCreateRequest(BaseModel):
    description: str = Field(default="", max_length=500)


class EvaluatorResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    type: EvaluatorType
    config: dict[str, Any]
    enabled: int
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class EvaluatorPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[EvaluatorResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class EvaluatorSampleTestRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    expected_output: str = Field(default="", alias="expectedOutput")
    actual_output: str = Field(alias="actualOutput", min_length=1)


class EvaluatorDraftTestRequest(EvaluatorSampleTestRequest):
    type: EvaluatorType
    config: dict[str, Any] = Field(default_factory=dict)


class EvaluatorSampleTestResponse(BaseModel):
    passed: bool
    score: float
    reason: str


class LlmEvaluatorDebugRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    model_config_id: int = Field(alias="modelConfigId", gt=0)
    prompt: str = Field(min_length=1)
    expected_output: str = Field(default="", alias="expectedOutput")
    actual_output: str = Field(alias="actualOutput", min_length=1)
    passing_score: float = Field(default=0.7, ge=0, le=1, alias="passingScore")


class LlmEvaluatorDebugResponse(EvaluatorSampleTestResponse):
    model_config_id: int = Field(alias="modelConfigId")
    debug_prompt: str = Field(alias="debugPrompt")
    raw_output: str = Field(alias="rawOutput")


TargetType = Literal["AGENT", "WORKFLOW", "CHATFLOW"]
RunStatus = Literal["RUNNING", "COMPLETED", "FAILED"]


class ExperimentCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(min_length=1, max_length=160)
    target_type: TargetType = Field(alias="targetType")
    target_id: int = Field(alias="targetId")
    eval_set_id: int = Field(alias="evalSetId")
    eval_set_version_id: int | None = Field(default=None, alias="evalSetVersionId")
    evaluator_ids: list[int] = Field(alias="evaluatorIds", min_length=1)
    evaluator_version_ids: list[int] = Field(default_factory=list, alias="evaluatorVersionIds")
    target_field_mapping: dict[str, str] = Field(default_factory=dict, alias="targetFieldMapping")
    evaluator_field_mapping: dict[str, str] = Field(default_factory=dict, alias="evaluatorFieldMapping")
    item_concurrency: int = Field(default=1, ge=1, le=20, alias="itemConcurrency")
    item_retry_count: int = Field(default=0, ge=0, le=5, alias="itemRetryCount")


class ExperimentResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    name: str
    target_type: TargetType = Field(alias="targetType")
    target_id: int = Field(alias="targetId")
    eval_set_id: int = Field(alias="evalSetId")
    eval_set_version_id: int | None = Field(default=None, alias="evalSetVersionId")
    evaluator_ids: list[int] = Field(alias="evaluatorIds")
    evaluator_version_ids: list[int] = Field(alias="evaluatorVersionIds")
    target_field_mapping: dict[str, str] = Field(alias="targetFieldMapping")
    evaluator_field_mapping: dict[str, str] = Field(alias="evaluatorFieldMapping")
    item_concurrency: int = Field(alias="itemConcurrency")
    item_retry_count: int = Field(alias="itemRetryCount")
    status: str
    latest_run_id: int | None = Field(alias="latestRunId")
    created_at: str = Field(alias="createdAt")
    updated_at: str = Field(alias="updatedAt")


class ExperimentPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[ExperimentResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class CaseResultResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    run_id: int = Field(alias="runId")
    eval_case_id: int = Field(alias="evalCaseId")
    input: str
    expected_output: str = Field(alias="expectedOutput")
    target_output: str = Field(alias="targetOutput")
    target_type: str = Field(alias="targetType")
    target_run_id: int | None = Field(alias="targetRunId")
    target_status: str = Field(alias="targetStatus")
    target_debug_url: str = Field(alias="targetDebugUrl")
    target_evidence_summary: dict[str, Any] = Field(alias="targetEvidenceSummary")
    status: str
    score: float
    evaluator_results: list[dict[str, Any]] = Field(alias="evaluatorResults")
    reason: str


class RunResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    id: int
    experiment_id: int = Field(alias="experimentId")
    status: RunStatus
    total_cases: int = Field(alias="totalCases")
    passed_cases: int = Field(alias="passedCases")
    failed_cases: int = Field(alias="failedCases")
    aggregate_score: float = Field(alias="aggregateScore")
    pass_rate: float = Field(alias="passRate")
    started_at: str | None = Field(alias="startedAt")
    finished_at: str | None = Field(alias="finishedAt")
    case_results: list[CaseResultResponse] = Field(default_factory=list, alias="caseResults")


class RunPageResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    list: list[RunResponse]
    total: int
    page: int
    page_size: int = Field(alias="pageSize")


class RunCompareCaseResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    eval_case_id: int = Field(alias="evalCaseId")
    input: str
    base_status: str = Field(alias="baseStatus")
    candidate_status: str = Field(alias="candidateStatus")
    base_score: float = Field(alias="baseScore")
    candidate_score: float = Field(alias="candidateScore")
    base_reason: str = Field(alias="baseReason")
    candidate_reason: str = Field(alias="candidateReason")


class RunCompareResponse(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    base_run_id: int = Field(alias="baseRunId")
    candidate_run_id: int = Field(alias="candidateRunId")
    base_score: float = Field(alias="baseScore")
    candidate_score: float = Field(alias="candidateScore")
    score_delta: float = Field(alias="scoreDelta")
    base_pass_rate: float = Field(alias="basePassRate")
    candidate_pass_rate: float = Field(alias="candidatePassRate")
    pass_rate_delta: float = Field(alias="passRateDelta")
    newly_failed_cases: list[RunCompareCaseResponse] = Field(alias="newlyFailedCases")
    recovered_cases: list[RunCompareCaseResponse] = Field(alias="recoveredCases")
    unchanged_failures: list[RunCompareCaseResponse] = Field(alias="unchangedFailures")


def format_datetime(value: datetime | str) -> str:
    if isinstance(value, datetime):
        return value.isoformat()
    return value
