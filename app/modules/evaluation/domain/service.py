from __future__ import annotations

import csv
from dataclasses import dataclass
import io
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.modules.audit.infra.repository import AuditRepository
from app.modules.evaluation.domain.fields import normalize_eval_set_fields, validate_case_against_fields
from app.modules.evaluation.domain.llm_debug import (
    LlmJudgeDebugResult,
    build_llm_judge_debug_prompt,
    parse_llm_judge_debug_response,
)
from app.modules.evaluation.domain.mapping import TARGET_OUTPUT_FIELD, ExperimentMapping, normalize_experiment_mapping
from app.modules.evaluation.domain.scoring import EvaluationSampleResult, evaluate_sample
from app.modules.evaluation.domain.target_adapters import EvaluationTargetRunner, TargetExecutionResult
from app.modules.evaluation.domain.versioning import build_eval_set_snapshot, next_eval_set_version_label
from app.modules.evaluation.infra.repository import EvaluationRepository
from app.modules.evaluation.web.schemas import (
    CaseResultResponse,
    EvalCaseCsvImportResponse,
    EvalCaseCreateRequest,
    EvalCaseResponse,
    EvalCaseUpdateRequest,
    EvalSetCreateRequest,
    EvalSetDetailResponse,
    EvalSetFieldsUpdateRequest,
    EvalSetPageResponse,
    EvalSetResponse,
    EvalSetUpdateRequest,
    EvalSetVersionCreateRequest,
    ExperimentCreateRequest,
    ExperimentPageResponse,
    ExperimentResponse,
    EvaluatorCreateRequest,
    EvaluatorDraftTestRequest,
    EvaluatorPageResponse,
    EvaluatorResponse,
    EvaluatorSampleTestRequest,
    EvaluatorSampleTestResponse,
    EvaluatorUpdateRequest,
    EvaluatorVersionCreateRequest,
    LlmEvaluatorDebugRequest,
    LlmEvaluatorDebugResponse,
    RunPageResponse,
    RunCompareCaseResponse,
    RunCompareResponse,
    RunResponse,
    format_datetime,
)
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.chat.domain.llm_request import ProviderBackedOpenAIChatClient, ProviderChatConfig


class EvaluationService:
    def __init__(
        self,
        repository: EvaluationRepository,
        audit_repository: AuditRepository | None = None,
        request_context: RequestContext | None = None,
    ) -> None:
        self._repository = repository
        self._audit_repository = audit_repository
        self._request_context = request_context

    def _audit(
        self,
        action: str,
        resource_type: str,
        resource_id: str | int,
        metadata: dict[str, Any],
    ) -> None:
        if self._audit_repository is None:
            return
        self._audit_repository.record(
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            status="succeeded",
            metadata=metadata,
            request_context=self._request_context,
        )

    def list_eval_sets(self, page: int, page_size: int, name: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_eval_sets(page, page_size, name)
        response = EvalSetPageResponse(
            list=[self._set_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create_eval_set(self, request: EvalSetCreateRequest) -> dict[str, Any]:
        row = self._repository.create_eval_set(
            {
                "name": request.name.strip(),
                "description": request.description.strip(),
            }
        )
        self._audit("EVALUATION_SET_CREATE", "EVALUATION_SET", int(row["id"]), {"name": row["name"]})
        return self._set_response(row).model_dump(by_alias=True)

    def get_eval_set(self, eval_set_id: int) -> dict[str, Any]:
        row = self._repository.get_eval_set(eval_set_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        response = EvalSetDetailResponse(
            **self._set_response(row).model_dump(),
            cases=[self._case_response(case) for case in self._repository.list_cases(eval_set_id)],
        )
        data = response.model_dump(by_alias=True)
        data.update(self._eval_set_version_state(eval_set_id))
        data["fieldSchema"] = self._eval_set_fields(eval_set_id)
        return data

    def update_eval_set(self, eval_set_id: int, request: EvalSetUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if request.name is not None:
            values["name"] = request.name.strip()
        if request.description is not None:
            values["description"] = request.description.strip()
        row = self._repository.update_eval_set(eval_set_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        return self._set_response(row).model_dump(by_alias=True)

    def delete_eval_set(self, eval_set_id: int) -> None:
        if not self._repository.delete_eval_set(eval_set_id):
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")

    def create_case(self, eval_set_id: int, request: EvalCaseCreateRequest) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        self._validate_case_fields(eval_set_id, request)
        row = self._repository.create_case(self._case_values(eval_set_id, request))
        self._audit("EVALUATION_CASE_CREATE", "EVALUATION_CASE", int(row["id"]), {"evalSetId": eval_set_id})
        return self._case_response(row).model_dump(by_alias=True)

    def update_case(self, eval_case_id: int, request: EvalCaseUpdateRequest) -> dict[str, Any]:
        existing = self._repository.get_case(eval_case_id)
        if existing is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval case not found")
        self._validate_case_fields(int(existing["eval_set_id"]), request)
        row = self._repository.update_case(
            eval_case_id,
            self._case_values(int(existing["eval_set_id"]), request),
        )
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval case not found")
        return self._case_response(row).model_dump(by_alias=True)

    def delete_case(self, eval_case_id: int) -> None:
        if not self._repository.delete_case(eval_case_id):
            raise BizError(ErrorCode.NOT_FOUND, "Eval case not found")

    def submit_eval_set_version(self, eval_set_id: int, request: EvalSetVersionCreateRequest) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        snapshot = self._current_eval_set_snapshot(eval_set_id)
        version = next_eval_set_version_label(self._repository.count_eval_set_versions(eval_set_id))
        row = self._repository.create_eval_set_version(
            eval_set_id=eval_set_id,
            version=version,
            schema_snapshot=snapshot["schema"],
            case_snapshot=snapshot["cases"],
            description=request.description.strip(),
        )
        return self._eval_set_version_response(row)

    def list_eval_set_versions(self, eval_set_id: int) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        rows = self._repository.list_eval_set_versions(eval_set_id)
        return {"list": [self._eval_set_version_response(row) for row in rows], "total": len(rows)}

    def get_eval_set_version(self, eval_set_id: int, version_id: int) -> dict[str, Any]:
        row = self._repository.get_eval_set_version(eval_set_id, version_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set version not found")
        return self._eval_set_version_response(row)

    def list_eval_set_related_experiments(self, eval_set_id: int) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        rows = self._repository.list_related_experiments(eval_set_id)
        return {
            "list": [self._related_experiment_response(row) for row in rows],
            "total": len(rows),
        }

    def list_eval_set_fields(self, eval_set_id: int) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        fields = self._eval_set_fields(eval_set_id)
        return {"list": fields, "total": len(fields)}

    def update_eval_set_fields(self, eval_set_id: int, request: EvalSetFieldsUpdateRequest) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        try:
            fields = normalize_eval_set_fields([field.model_dump(by_alias=True) for field in request.fields])
        except ValueError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        rows = self._repository.replace_eval_set_fields(eval_set_id, fields)
        normalized = [self._field_row(row) for row in rows]
        return {"list": normalized, "total": len(normalized)}

    def import_cases_csv(self, eval_set_id: int, content: bytes) -> dict[str, Any]:
        if self._repository.get_eval_set(eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        text = content.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"input", "expectedOutput"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise BizError(ErrorCode.BAD_REQUEST, "CSV requires input and expectedOutput columns")
        created_count = 0
        for row in reader:
            input_text = str(row.get("input") or "").strip()
            expected_output = str(row.get("expectedOutput") or "").strip()
            if not input_text or not expected_output:
                continue
            tags = [tag.strip() for tag in str(row.get("tags") or "").split("|")]
            self.create_case(
                eval_set_id,
                EvalCaseCreateRequest(
                    input=input_text,
                    expectedOutput=expected_output,
                    tags=tags,
                    metadata={},
                ),
            )
            created_count += 1
        return EvalCaseCsvImportResponse(createdCount=created_count).model_dump(by_alias=True)

    def list_evaluators(self, page: int, page_size: int, name: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_evaluators(page, page_size, name)
        response = EvaluatorPageResponse(
            list=[self._evaluator_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create_evaluator(self, request: EvaluatorCreateRequest) -> dict[str, Any]:
        self._validate_evaluator_config(request.type, request.config)
        row = self._repository.create_evaluator(
            {
                "name": request.name.strip(),
                "type": request.type,
                "config": self._normalize_evaluator_config(request.type, request.config),
            }
        )
        self._audit("EVALUATOR_CREATE", "EVALUATOR", int(row["id"]), {"name": row["name"], "type": row["type"]})
        return self._evaluator_response(row).model_dump(by_alias=True)

    def get_evaluator(self, evaluator_id: int) -> dict[str, Any]:
        row = self._repository.get_evaluator(evaluator_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        return self._evaluator_response(row).model_dump(by_alias=True)

    def update_evaluator(self, evaluator_id: int, request: EvaluatorUpdateRequest) -> dict[str, Any]:
        self._validate_evaluator_config(request.type, request.config)
        values: dict[str, Any] = {
            "name": request.name.strip(),
            "type": request.type,
            "config": self._normalize_evaluator_config(request.type, request.config),
        }
        if request.enabled is not None:
            values["enabled"] = bool(request.enabled)
        row = self._repository.update_evaluator(evaluator_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        return self._evaluator_response(row).model_dump(by_alias=True)

    def delete_evaluator(self, evaluator_id: int) -> None:
        if not self._repository.delete_evaluator(evaluator_id):
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")

    def publish_evaluator_version(self, evaluator_id: int, request: EvaluatorVersionCreateRequest) -> dict[str, Any]:
        row = self._repository.get_evaluator(evaluator_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        version = next_eval_set_version_label(self._repository.count_evaluator_versions(evaluator_id))
        created = self._repository.create_evaluator_version(
            evaluator_id=evaluator_id,
            version=version,
            evaluator_type=str(row["type"]),
            config_snapshot=dict(row["config"] or {}),
            input_schema=self._evaluator_input_schema(str(row["type"])),
            description=request.description.strip(),
        )
        return self._evaluator_version_response(created)

    def list_evaluator_versions(self, evaluator_id: int) -> dict[str, Any]:
        if self._repository.get_evaluator(evaluator_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        rows = self._repository.list_evaluator_versions(evaluator_id)
        return {"list": [self._evaluator_version_response(row) for row in rows], "total": len(rows)}

    def list_evaluator_presets(self) -> dict[str, Any]:
        presets = [
            {
                "key": "EXACT_MATCH",
                "name": "Exact Match",
                "description": "Pass when actual output exactly matches expected output.",
                "enabled": True,
                "config": {"ignoreCase": True},
            },
            {
                "key": "CONTAINS_KEYWORDS",
                "name": "Contains Keywords",
                "description": "Pass when actual output contains configured keywords.",
                "enabled": True,
                "config": {"keywords": ["keyword"], "matchMode": "all", "ignoreCase": True},
            },
            {
                "key": "LLM_JUDGE",
                "name": "LLM Judge",
                "description": "Use a model to produce score and reason from a rubric.",
                "enabled": True,
                "config": {"rubric": "Judge whether actual output satisfies expected output.", "passingScore": 0.7},
            },
            {
                "key": "CODE_EVALUATOR",
                "name": "Code Evaluator",
                "description": "Disabled until sandboxing and timeout controls are specified.",
                "enabled": False,
                "config": {},
            },
        ]
        return {"list": presets, "total": len(presets)}

    def test_draft_evaluator(self, request: EvaluatorDraftTestRequest) -> dict[str, Any]:
        self._validate_evaluator_config(request.type, request.config)
        if request.type == "LLM_JUDGE":
            return self._sample_response(
                self._evaluate_llm_judge(
                    self._normalize_evaluator_config(request.type, request.config),
                    request.expected_output,
                    request.actual_output,
                )
            ).model_dump()
        return self._sample_response(
            evaluate_sample(
                request.type,
                self._normalize_evaluator_config(request.type, request.config),
                request.expected_output,
                request.actual_output,
            )
        ).model_dump()

    def test_evaluator(self, evaluator_id: int, request: EvaluatorSampleTestRequest) -> dict[str, Any]:
        row = self._repository.get_evaluator(evaluator_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        if row["type"] == "LLM_JUDGE":
            return self._sample_response(
                self._evaluate_llm_judge(
                    dict(row["config"] or {}),
                    request.expected_output,
                    request.actual_output,
                )
            ).model_dump()
        return self._sample_response(
            evaluate_sample(
                row["type"],
                dict(row["config"] or {}),
                request.expected_output,
                request.actual_output,
            )
        ).model_dump()

    def debug_llm_evaluator(self, request: LlmEvaluatorDebugRequest) -> dict[str, Any]:
        debug = self._debug_llm_judge(
            {
                "modelConfigId": request.model_config_id,
                "rubric": request.prompt,
                "passingScore": request.passing_score,
            },
            request.expected_output,
            request.actual_output,
        )
        response = LlmEvaluatorDebugResponse(
            passed=debug.result.passed,
            score=debug.result.score,
            reason=debug.result.reason,
            modelConfigId=request.model_config_id,
            debugPrompt=debug.prompt,
            rawOutput=debug.result.raw_output,
        )
        return response.model_dump(by_alias=True)

    def list_experiments(self, page: int, page_size: int, name: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_experiments(page, page_size, name)
        response = ExperimentPageResponse(
            list=[self._experiment_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create_experiment(self, request: ExperimentCreateRequest) -> dict[str, Any]:
        self._validate_target(request.target_type, request.target_id)
        if self._repository.get_eval_set(request.eval_set_id) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        if request.eval_set_version_id is not None:
            if self._repository.get_eval_set_version(request.eval_set_id, request.eval_set_version_id) is None:
                raise BizError(ErrorCode.NOT_FOUND, "Eval set version not found")
        missing = [evaluator_id for evaluator_id in request.evaluator_ids if self._repository.get_evaluator(evaluator_id) is None]
        if missing:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        evaluator_version_ids = self._validate_evaluator_versions_for_request(
            request.evaluator_ids,
            request.evaluator_version_ids,
        )
        mapping = self._experiment_mapping_for_request(request)
        row = self._repository.create_experiment(
            {
                "name": request.name.strip(),
                "target_type": request.target_type,
                "target_id": request.target_id,
                "eval_set_id": request.eval_set_id,
                "eval_set_version_id": request.eval_set_version_id,
                "evaluator_ids": request.evaluator_ids,
                "evaluator_version_ids": evaluator_version_ids,
                "target_field_mapping": mapping.target_field_mapping,
                "evaluator_field_mapping": mapping.evaluator_field_mapping,
                "item_concurrency": mapping.item_concurrency,
                "item_retry_count": mapping.item_retry_count,
            }
        )
        self._audit(
            "EVALUATION_EXPERIMENT_CREATE",
            "EVALUATION_EXPERIMENT",
            int(row["id"]),
            {"targetType": request.target_type, "targetId": request.target_id, "evalSetId": request.eval_set_id},
        )
        return self._experiment_response(row).model_dump(by_alias=True)

    def run_experiment(self, experiment_id: int) -> dict[str, Any]:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            raise BizError(ErrorCode.NOT_FOUND, "Experiment not found")
        cases = self._repository.list_cases(int(experiment["eval_set_id"]))
        if not cases:
            raise BizError(ErrorCode.BAD_REQUEST, "Eval set has no cases")
        evaluators = self._evaluators_for_experiment(experiment)
        run = self._repository.create_run(experiment_id, len(cases))
        case_results: list[dict[str, Any]] = []
        for eval_case in cases:
            case_results.append(self._execute_case_with_retry(int(run["id"]), experiment, eval_case, evaluators))
        finished = self._finish_run_from_case_results(int(run["id"]), case_results)
        self._repository.update_experiment_latest_run(experiment_id, int(run["id"]))
        if finished is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        data = self._run_response(finished, case_results).model_dump(by_alias=True)
        self._audit(
            "EVALUATION_RUN",
            "EVALUATION_RUN",
            int(finished["id"]),
            {"experimentId": experiment_id, "status": data["status"], "totalCases": data["totalCases"]},
        )
        return data

    def list_runs(self, page: int, page_size: int, status: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_runs(page, page_size, status)
        response = RunPageResponse(
            list=[self._run_response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def get_run_detail(self, run_id: int, case_status: str | None) -> dict[str, Any]:
        row = self._repository.get_run(run_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        normalized_status = case_status.upper() if case_status else None
        case_results = self._repository.list_case_results(run_id, normalized_status)
        return self._run_response(row, case_results).model_dump(by_alias=True)

    def compare_runs(self, base_run_id: int, candidate_run_id: int) -> dict[str, Any]:
        base_run = self._repository.get_run(base_run_id)
        candidate_run = self._repository.get_run(candidate_run_id)
        if base_run is None or candidate_run is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        base_cases = {
            int(row["eval_case_id"]): row
            for row in self._repository.list_case_results(base_run_id)
        }
        candidate_cases = {
            int(row["eval_case_id"]): row
            for row in self._repository.list_case_results(candidate_run_id)
        }
        newly_failed: list[RunCompareCaseResponse] = []
        recovered: list[RunCompareCaseResponse] = []
        unchanged_failures: list[RunCompareCaseResponse] = []
        for eval_case_id in sorted(set(base_cases) | set(candidate_cases)):
            base_case = base_cases.get(eval_case_id)
            candidate_case = candidate_cases.get(eval_case_id)
            if candidate_case is None:
                continue
            base_status = str(base_case["status"]) if base_case else "MISSING"
            candidate_status = str(candidate_case["status"])
            change = self._compare_case_response(eval_case_id, base_case, candidate_case)
            if candidate_status == "FAILED" and base_status != "FAILED":
                newly_failed.append(change)
            elif base_status == "FAILED" and candidate_status == "PASSED":
                recovered.append(change)
            elif base_status == "FAILED" and candidate_status == "FAILED":
                unchanged_failures.append(change)
        response = RunCompareResponse(
            baseRunId=base_run_id,
            candidateRunId=candidate_run_id,
            baseScore=float(base_run["aggregate_score"] or 0.0),
            candidateScore=float(candidate_run["aggregate_score"] or 0.0),
            scoreDelta=round(float(candidate_run["aggregate_score"] or 0.0) - float(base_run["aggregate_score"] or 0.0), 4),
            basePassRate=float(base_run["pass_rate"] or 0.0),
            candidatePassRate=float(candidate_run["pass_rate"] or 0.0),
            passRateDelta=round(float(candidate_run["pass_rate"] or 0.0) - float(base_run["pass_rate"] or 0.0), 4),
            newlyFailedCases=newly_failed,
            recoveredCases=recovered,
            unchangedFailures=unchanged_failures,
        )
        return response.model_dump(by_alias=True)

    def export_run_csv(self, run_id: int) -> str:
        row = self._repository.get_run(run_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        output = io.StringIO()
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "status",
                "input",
                "expected_output",
                "target_output",
                "score",
                "reason",
            ],
        )
        writer.writeheader()
        for result in self._repository.list_case_results(run_id):
            writer.writerow(
                {
                    "status": result["status"],
                    "input": result["input"],
                    "expected_output": result["expected_output"],
                    "target_output": result["target_output"],
                    "score": result["score"],
                    "reason": result["reason"] or "",
                }
            )
        return output.getvalue()

    def rerun_case_result(self, run_id: int, case_result_id: int) -> dict[str, Any]:
        source_run = self._repository.get_run(run_id)
        if source_run is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        source_case = self._repository.get_case_result(case_result_id)
        if source_case is None or int(source_case["run_id"]) != run_id:
            raise BizError(ErrorCode.NOT_FOUND, "Case result not found")
        experiment_id = int(source_run["experiment_id"])
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            raise BizError(ErrorCode.NOT_FOUND, "Experiment not found")
        evaluators = self._evaluators_for_experiment(experiment)
        rerun = self._repository.create_run(experiment_id, 1)
        case_result = self._execute_case(
            int(rerun["id"]),
            experiment,
            {
                "id": int(source_case["eval_case_id"]),
                "input": source_case["input"],
                "expected_output": source_case["expected_output"],
            },
            evaluators,
        )
        finished = self._finish_run_from_case_results(int(rerun["id"]), [case_result])
        self._repository.update_experiment_latest_run(experiment_id, int(rerun["id"]))
        if finished is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        return self._run_response(finished, [case_result]).model_dump(by_alias=True)

    def _case_values(self, eval_set_id: int, request: EvalCaseCreateRequest) -> dict[str, Any]:
        return {
            "eval_set_id": eval_set_id,
            "input": request.input.strip(),
            "expected_output": request.expected_output.strip(),
            "tags": _normalize_tags(request.tags),
            "case_metadata": request.metadata,
        }

    def _set_response(self, row: dict[str, Any]) -> EvalSetResponse:
        return EvalSetResponse(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            caseCount=int(row.get("case_count") or 0),
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _current_eval_set_snapshot(self, eval_set_id: int) -> dict[str, Any]:
        return build_eval_set_snapshot(fields=self._eval_set_fields(eval_set_id), cases=self._repository.list_cases(eval_set_id))

    def _eval_set_version_state(self, eval_set_id: int) -> dict[str, Any]:
        latest = self._repository.latest_eval_set_version(eval_set_id)
        if latest is None:
            return {"latestVersion": "", "versionCount": 0, "draftChanged": True}
        current = self._current_eval_set_snapshot(eval_set_id)
        latest_snapshot = {
            "schema": latest["schema_snapshot"] or [],
            "cases": latest["case_snapshot"] or [],
            "caseCount": len(latest["case_snapshot"] or []),
        }
        return {
            "latestVersion": latest["version"],
            "versionCount": self._repository.count_eval_set_versions(eval_set_id),
            "draftChanged": current != latest_snapshot,
        }

    def _eval_set_version_response(self, row: dict[str, Any]) -> dict[str, Any]:
        case_snapshot = list(row["case_snapshot"] or [])
        schema_snapshot = list(row["schema_snapshot"] or [])
        return {
            "id": int(row["id"]),
            "evalSetId": int(row["eval_set_id"]),
            "version": row["version"],
            "description": row["description"] or "",
            "schemaSnapshot": schema_snapshot,
            "caseSnapshot": case_snapshot,
            "caseCount": len(case_snapshot),
            "createdBy": row["created_by"],
            "createdAt": format_datetime(row["created_at"]),
        }

    def _eval_set_fields(self, eval_set_id: int) -> list[dict[str, Any]]:
        rows = self._repository.list_eval_set_fields(eval_set_id)
        if not rows:
            return normalize_eval_set_fields(None)
        return [self._field_row(row) for row in rows]

    def _field_row(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "key": row["key"],
            "label": row["label"],
            "contentType": row["content_type"],
            "required": bool(row["required"]),
            "displayOrder": int(row["display_order"]),
        }

    def _validate_case_fields(self, eval_set_id: int, request: EvalCaseCreateRequest) -> None:
        try:
            validate_case_against_fields(
                self._eval_set_fields(eval_set_id),
                input_value=request.input.strip(),
                expected_output=request.expected_output.strip(),
                metadata=request.metadata,
            )
        except ValueError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc

    def _case_response(self, row: dict[str, Any]) -> EvalCaseResponse:
        return EvalCaseResponse(
            id=int(row["id"]),
            evalSetId=int(row["eval_set_id"]),
            input=row["input"],
            expectedOutput=row["expected_output"],
            tags=list(row["tags"] or []),
            metadata=dict(row["case_metadata"] or {}),
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _evaluator_response(self, row: dict[str, Any]) -> EvaluatorResponse:
        return EvaluatorResponse(
            id=int(row["id"]),
            name=row["name"],
            type=row["type"],
            config=dict(row["config"] or {}),
            enabled=1 if row["enabled"] else 0,
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _evaluator_version_response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "evaluatorId": int(row["evaluator_id"]),
            "version": row["version"],
            "evaluatorType": row["evaluator_type"],
            "configSnapshot": dict(row["config_snapshot"] or {}),
            "inputSchema": list(row["input_schema"] or []),
            "description": row["description"] or "",
            "createdAt": format_datetime(row["created_at"]),
        }

    def _evaluator_input_schema(self, evaluator_type: str) -> list[dict[str, Any]]:
        if evaluator_type == "LLM_JUDGE":
            return [
                {"key": "expectedOutput", "label": "Expected output", "required": False},
                {"key": "actualOutput", "label": "Actual output", "required": True},
                {"key": "rubric", "label": "Rubric", "required": True},
            ]
        return [
            {"key": "expectedOutput", "label": "Expected output", "required": False},
            {"key": "actualOutput", "label": "Actual output", "required": True},
        ]

    def _experiment_response(self, row: dict[str, Any]) -> ExperimentResponse:
        return ExperimentResponse(
            id=int(row["id"]),
            name=row["name"],
            targetType=row["target_type"],
            targetId=int(row["target_id"]),
            evalSetId=int(row["eval_set_id"]),
            evalSetVersionId=int(row["eval_set_version_id"]) if row.get("eval_set_version_id") is not None else None,
            evaluatorIds=[int(item) for item in list(row["evaluator_ids"] or [])],
            evaluatorVersionIds=[int(item) for item in list(row.get("evaluator_version_ids") or [])],
            targetFieldMapping=dict(row.get("target_field_mapping") or {"userMessage": "input"}),
            evaluatorFieldMapping=dict(row.get("evaluator_field_mapping") or {"expectedOutput": "expectedOutput", "actualOutput": TARGET_OUTPUT_FIELD}),
            itemConcurrency=int(row.get("item_concurrency") or 1),
            itemRetryCount=int(row.get("item_retry_count") or 0),
            status=row["status"],
            latestRunId=int(row["latest_run_id"]) if row["latest_run_id"] is not None else None,
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _experiment_mapping_for_request(self, request: ExperimentCreateRequest) -> ExperimentMapping:
        try:
            return normalize_experiment_mapping(
                fields=[field["key"] for field in self._eval_set_fields(request.eval_set_id)],
                target_field_mapping=request.target_field_mapping,
                evaluator_field_mapping=request.evaluator_field_mapping,
                item_concurrency=request.item_concurrency,
                item_retry_count=request.item_retry_count,
            )
        except ValueError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc

    def _validate_evaluator_versions_for_request(
        self,
        evaluator_ids: list[int],
        evaluator_version_ids: list[int],
    ) -> list[int]:
        if not evaluator_version_ids:
            return []
        selected_evaluator_ids = {int(item) for item in evaluator_ids}
        seen_versions: set[int] = set()
        seen_evaluators: set[int] = set()
        normalized: list[int] = []
        for evaluator_version_id in evaluator_version_ids:
            version_id = int(evaluator_version_id)
            if version_id in seen_versions:
                raise BizError(ErrorCode.BAD_REQUEST, "Evaluator version ids must be unique")
            version = self._repository.get_evaluator_version(version_id)
            if version is None:
                raise BizError(ErrorCode.NOT_FOUND, "Evaluator version not found")
            evaluator_id = int(version["evaluator_id"])
            if evaluator_id not in selected_evaluator_ids:
                raise BizError(ErrorCode.BAD_REQUEST, "Evaluator version must belong to selected evaluator")
            if evaluator_id in seen_evaluators:
                raise BizError(ErrorCode.BAD_REQUEST, "Only one evaluator version can be selected per evaluator")
            seen_versions.add(version_id)
            seen_evaluators.add(evaluator_id)
            normalized.append(version_id)
        return normalized

    def _evaluators_for_experiment(self, experiment: dict[str, Any]) -> list[dict[str, Any]]:
        evaluator_version_ids = [int(item) for item in list(experiment.get("evaluator_version_ids") or [])]
        versioned_by_evaluator: dict[int, dict[str, Any]] = {}
        for version_id in evaluator_version_ids:
            version = self._repository.get_evaluator_version(version_id)
            if version is None:
                raise BizError(ErrorCode.NOT_FOUND, "Evaluator version not found")
            evaluator = self._require_evaluator(int(version["evaluator_id"]))
            versioned_by_evaluator[int(version["evaluator_id"])] = self._evaluator_from_version(evaluator, version)
        return [
            versioned_by_evaluator.get(int(evaluator_id)) or self._require_evaluator(int(evaluator_id))
            for evaluator_id in list(experiment["evaluator_ids"] or [])
        ]

    def _evaluator_from_version(self, evaluator: dict[str, Any], version: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(version["evaluator_id"]),
            "name": evaluator["name"],
            "type": version["evaluator_type"],
            "config": dict(version["config_snapshot"] or {}),
            "version_id": int(version["id"]),
            "version": version["version"],
        }

    def _experiment_mapping_for_run(self, experiment: dict[str, Any]) -> ExperimentMapping:
        try:
            return normalize_experiment_mapping(
                fields=[field["key"] for field in self._eval_set_fields(int(experiment["eval_set_id"]))],
                target_field_mapping=dict(experiment.get("target_field_mapping") or {}),
                evaluator_field_mapping=dict(experiment.get("evaluator_field_mapping") or {}),
                item_concurrency=int(experiment.get("item_concurrency") or 1),
                item_retry_count=int(experiment.get("item_retry_count") or 0),
            )
        except ValueError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc

    def _related_experiment_response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "targetType": row["target_type"],
            "targetId": int(row["target_id"]),
            "evalSetId": int(row["eval_set_id"]),
            "evalSetVersionId": int(row["eval_set_version_id"]) if row.get("eval_set_version_id") is not None else None,
            "evalSetVersion": row.get("eval_set_version") or "",
            "status": row["status"],
            "latestRunId": int(row["latest_run_id"]) if row.get("latest_run_id") is not None else None,
            "latestRunStatus": row.get("latest_run_status") or "",
            "latestRunScore": float(row["latest_run_score"]) if row.get("latest_run_score") is not None else None,
            "latestRunPassRate": float(row["latest_run_pass_rate"]) if row.get("latest_run_pass_rate") is not None else None,
            "latestRunFinishedAt": format_datetime(row["latest_run_finished_at"]) if row.get("latest_run_finished_at") else None,
            "createdAt": format_datetime(row["created_at"]),
            "updatedAt": format_datetime(row["updated_at"]),
        }

    def _run_response(self, row: dict[str, Any], case_results: list[dict[str, Any]] | None = None) -> RunResponse:
        return RunResponse(
            id=int(row["id"]),
            experimentId=int(row["experiment_id"]),
            status=row["status"],
            totalCases=int(row["total_cases"] or 0),
            passedCases=int(row["passed_cases"] or 0),
            failedCases=int(row["failed_cases"] or 0),
            aggregateScore=float(row["aggregate_score"] or 0.0),
            passRate=float(row["pass_rate"] or 0.0),
            startedAt=format_datetime(row["started_at"]) if row["started_at"] else None,
            finishedAt=format_datetime(row["finished_at"]) if row["finished_at"] else None,
            caseResults=[self._case_result_response(result) for result in case_results or []],
        )

    def _case_result_response(self, row: dict[str, Any]) -> CaseResultResponse:
        return CaseResultResponse(
            id=int(row["id"]),
            runId=int(row["run_id"]),
            evalCaseId=int(row["eval_case_id"]),
            input=row["input"],
            expectedOutput=row["expected_output"],
            targetOutput=row["target_output"],
            targetType=str(row.get("target_type") or ""),
            targetRunId=int(row["target_run_id"]) if row.get("target_run_id") is not None else None,
            targetStatus=str(row.get("target_status") or ""),
            targetDebugUrl=str(row.get("target_debug_url") or ""),
            targetEvidenceSummary=dict(row.get("target_evidence_summary") or {}),
            status=row["status"],
            score=float(row["score"] or 0.0),
            evaluatorResults=list(row["evaluator_results"] or []),
            reason=row["reason"] or "",
        )

    def _compare_case_response(
        self,
        eval_case_id: int,
        base_case: dict[str, Any] | None,
        candidate_case: dict[str, Any],
    ) -> RunCompareCaseResponse:
        return RunCompareCaseResponse(
            evalCaseId=eval_case_id,
            input=str(candidate_case.get("input") or (base_case or {}).get("input") or ""),
            baseStatus=str((base_case or {}).get("status") or "MISSING"),
            candidateStatus=str(candidate_case["status"]),
            baseScore=float((base_case or {}).get("score") or 0.0),
            candidateScore=float(candidate_case.get("score") or 0.0),
            baseReason=str((base_case or {}).get("reason") or ""),
            candidateReason=str(candidate_case.get("reason") or ""),
        )

    def _sample_response(self, result: EvaluationSampleResult) -> EvaluatorSampleTestResponse:
        return EvaluatorSampleTestResponse(
            passed=result.passed,
            score=result.score,
            reason=result.reason,
        )

    def _validate_evaluator_config(self, evaluator_type: str, config: dict[str, Any]) -> None:
        if evaluator_type == "CONTAINS_KEYWORDS":
            keywords = self._normalize_evaluator_config(evaluator_type, config).get("keywords", [])
            if not keywords:
                raise BizError(ErrorCode.BAD_REQUEST, "Contains Keywords evaluator requires at least one keyword")
        if evaluator_type == "LLM_JUDGE" and not config.get("modelConfigId"):
            raise BizError(ErrorCode.BAD_REQUEST, "LLM Judge evaluator requires modelConfigId")

    def _normalize_evaluator_config(self, evaluator_type: str, config: dict[str, Any]) -> dict[str, Any]:
        if evaluator_type == "EXACT_MATCH":
            return {"ignoreCase": bool(config.get("ignoreCase", False))}
        if evaluator_type == "CONTAINS_KEYWORDS":
            return {
                "keywords": _normalize_tags([str(item) for item in config.get("keywords", [])]),
                "matchMode": str(config.get("matchMode", "all")).lower(),
                "ignoreCase": bool(config.get("ignoreCase", True)),
            }
        if evaluator_type == "LLM_JUDGE":
            return {
                "modelConfigId": int(config.get("modelConfigId") or 0),
                "rubric": str(config.get("rubric") or "Judge whether actual output satisfies expected output."),
                "passingScore": float(config.get("passingScore") or 0.7),
            }
        return config

    def _require_evaluator(self, evaluator_id: int) -> dict[str, Any]:
        evaluator = self._repository.get_evaluator(evaluator_id)
        if evaluator is None:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        return evaluator

    def _validate_target(self, target_type: str, target_id: int) -> None:
        if target_type == "AGENT":
            if not self._repository.agent_exists(target_id):
                raise BizError(ErrorCode.NOT_FOUND, "Agent target not found")
            return
        if target_type in {"WORKFLOW", "CHATFLOW"}:
            if not self._repository.workflow_exists(target_id, target_type):
                raise BizError(ErrorCode.NOT_FOUND, f"{target_type.title()} target not found")
            return
        raise BizError(ErrorCode.BAD_REQUEST, "Unsupported evaluation target type")

    def _evaluate_case(
        self,
        evaluator: dict[str, Any],
        expected_output: str,
        target_output: str,
    ) -> dict[str, Any]:
        if evaluator["type"] == "LLM_JUDGE":
            result = self._evaluate_llm_judge(dict(evaluator["config"] or {}), expected_output, target_output)
        else:
            result = evaluate_sample(
                evaluator["type"],
                dict(evaluator["config"] or {}),
                expected_output,
                target_output,
            )
        return {
            "evaluatorId": int(evaluator["id"]),
            "evaluatorName": evaluator["name"],
            "type": evaluator["type"],
            "evaluatorVersionId": int(evaluator["version_id"]) if evaluator.get("version_id") is not None else None,
            "version": evaluator.get("version") or "",
            "passed": result.passed,
            "score": result.score,
            "reason": result.reason,
        }

    def _execute_case(
        self,
        run_id: int,
        experiment: dict[str, Any],
        eval_case: dict[str, Any],
        evaluators: list[dict[str, Any]],
    ) -> dict[str, Any]:
        mapping = self._experiment_mapping_for_run(experiment)
        target_input = self._mapped_case_value(
            eval_case,
            mapping.target_field_mapping.get("userMessage", "input"),
            target_output="",
        )
        target_result = self._run_target(
            str(experiment["target_type"]),
            int(experiment["target_id"]),
            str(target_input),
        )
        target_output = target_result.output
        expected_output = self._mapped_case_value(
            eval_case,
            mapping.evaluator_field_mapping.get("expectedOutput", "expectedOutput"),
            target_output=target_output,
        )
        actual_output = self._mapped_case_value(
            eval_case,
            mapping.evaluator_field_mapping.get("actualOutput", TARGET_OUTPUT_FIELD),
            target_output=target_output,
        )
        evaluator_results = [
            self._evaluate_case(evaluator, str(expected_output), str(actual_output))
            for evaluator in evaluators
        ]
        score = sum(float(result["score"]) for result in evaluator_results) / len(evaluator_results)
        passed = all(bool(result["passed"]) for result in evaluator_results)
        return self._repository.create_case_result(
            {
                "run_id": run_id,
                "eval_case_id": int(eval_case["id"]),
                "input": str(target_input),
                "expected_output": str(expected_output),
                "target_output": str(actual_output),
                "target_type": target_result.target_type,
                "target_run_id": target_result.target_run_id,
                "target_status": target_result.status,
                "target_debug_url": target_result.debug_url,
                "target_evidence_summary": target_result.evidence_summary,
                "status": "PASSED" if passed else "FAILED",
                "score": round(score, 4),
                "evaluator_results": evaluator_results,
                "reason": "; ".join(str(result["reason"]) for result in evaluator_results),
            }
        )

    def _execute_case_with_retry(
        self,
        run_id: int,
        experiment: dict[str, Any],
        eval_case: dict[str, Any],
        evaluators: list[dict[str, Any]],
    ) -> dict[str, Any]:
        retries = max(0, int(experiment.get("item_retry_count") or 0))
        last_error: Exception | None = None
        for _ in range(retries + 1):
            try:
                return self._execute_case(run_id, experiment, eval_case, evaluators)
            except Exception as exc:  # pragma: no cover - exercised by future fault-injection tests
                last_error = exc
        if last_error is not None:
            raise last_error
        raise BizError(ErrorCode.BAD_REQUEST, "Evaluation case execution failed")

    def _mapped_case_value(self, eval_case: dict[str, Any], field_key: str, *, target_output: str) -> str:
        if field_key == TARGET_OUTPUT_FIELD:
            return target_output
        if field_key == "input":
            return str(eval_case.get("input") or "")
        if field_key == "expectedOutput":
            return str(eval_case.get("expected_output") or "")
        metadata = dict(eval_case.get("case_metadata") or {})
        return str(metadata.get(field_key) or "")

    def _finish_run_from_case_results(
        self,
        run_id: int,
        case_results: list[dict[str, Any]],
    ) -> dict[str, Any] | None:
        passed_cases = sum(1 for result in case_results if result["status"] == "PASSED")
        failed_cases = len(case_results) - passed_cases
        aggregate_score = round(sum(float(result["score"]) for result in case_results) / len(case_results), 4)
        pass_rate = round(passed_cases / len(case_results), 4)
        return self._repository.finish_run(
            run_id,
            "COMPLETED",
            passed_cases,
            failed_cases,
            aggregate_score,
            pass_rate,
        )

    def _run_target(self, target_type: str, target_id: int, content: str) -> TargetExecutionResult:
        self._validate_target(target_type, target_id)
        return EvaluationTargetRunner(self._repository.session, self._request_context).execute(
            target_type,
            target_id,
            content,
        )

    def _evaluate_llm_judge(
        self,
        config: dict[str, Any],
        expected_output: str,
        actual_output: str,
    ) -> EvaluationSampleResult:
        result = self._debug_llm_judge(config, expected_output, actual_output).result
        return EvaluationSampleResult(
            passed=result.passed,
            score=result.score,
            reason=result.reason,
        )

    def _debug_llm_judge(
        self,
        config: dict[str, Any],
        expected_output: str,
        actual_output: str,
    ) -> "_LlmJudgeDebugPayload":
        model_config_id = int(config.get("modelConfigId") or 0)
        if model_config_id <= 0:
            raise BizError(ErrorCode.BAD_REQUEST, "LLM Judge evaluator requires modelConfigId")
        model_config = ProviderModelFacade(self._repository.session).get_enabled_model_config(model_config_id)
        client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type=model_config.provider_type,
                base_url=model_config.provider_base_url,
                auth_config=model_config.provider_auth_config,
            )
        )
        prompt = build_llm_judge_debug_prompt(
            prompt_template=str(config.get("rubric") or ""),
            expected_output=expected_output,
            actual_output=actual_output,
        )
        payload = {
            "model": model_config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 300,
        }
        raw = client.complete(payload)
        content = str(raw.get("choices", [{}])[0].get("message", {}).get("content") or "")
        return _LlmJudgeDebugPayload(
            prompt=prompt,
            result=parse_llm_judge_debug_response(content, passing_score=float(config.get("passingScore") or 0.7)),
        )


@dataclass(frozen=True)
class _LlmJudgeDebugPayload:
    prompt: str
    result: LlmJudgeDebugResult


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized
