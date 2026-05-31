from __future__ import annotations

import csv
import io
import json
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.chat.domain.service import ChatService
from app.modules.chat.infra.repository import ChatRepository
from app.modules.chat.web.schemas import ChatMessageCreateRequest, ChatSessionCreateRequest
from app.modules.evaluation.domain.scoring import EvaluationSampleResult, evaluate_sample
from app.modules.evaluation.infra.repository import EvaluationRepository
from app.modules.evaluation.web.schemas import (
    CaseResultResponse,
    EvalCaseCsvImportResponse,
    EvalCaseCreateRequest,
    EvalCaseResponse,
    EvalCaseUpdateRequest,
    EvalSetCreateRequest,
    EvalSetDetailResponse,
    EvalSetPageResponse,
    EvalSetResponse,
    EvalSetUpdateRequest,
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
    RunPageResponse,
    RunCompareCaseResponse,
    RunCompareResponse,
    RunResponse,
    format_datetime,
)
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.mcp.api.facade import McpFacade
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.chat.domain.llm_request import ProviderBackedOpenAIChatClient, ProviderChatConfig
from app.modules.workflow.api.facade import WorkflowFacade


class EvaluationService:
    def __init__(self, repository: EvaluationRepository) -> None:
        self._repository = repository

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
        return self._set_response(row).model_dump(by_alias=True)

    def get_eval_set(self, eval_set_id: int) -> dict[str, Any]:
        row = self._repository.get_eval_set(eval_set_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval set not found")
        response = EvalSetDetailResponse(
            **self._set_response(row).model_dump(),
            cases=[self._case_response(case) for case in self._repository.list_cases(eval_set_id)],
        )
        return response.model_dump(by_alias=True)

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
        row = self._repository.create_case(self._case_values(eval_set_id, request))
        return self._case_response(row).model_dump(by_alias=True)

    def update_case(self, eval_case_id: int, request: EvalCaseUpdateRequest) -> dict[str, Any]:
        existing = self._repository.get_case(eval_case_id)
        if existing is None:
            raise BizError(ErrorCode.NOT_FOUND, "Eval case not found")
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
        missing = [evaluator_id for evaluator_id in request.evaluator_ids if self._repository.get_evaluator(evaluator_id) is None]
        if missing:
            raise BizError(ErrorCode.NOT_FOUND, "Evaluator not found")
        row = self._repository.create_experiment(
            {
                "name": request.name.strip(),
                "target_type": request.target_type,
                "target_id": request.target_id,
                "eval_set_id": request.eval_set_id,
                "evaluator_ids": request.evaluator_ids,
            }
        )
        return self._experiment_response(row).model_dump(by_alias=True)

    def run_experiment(self, experiment_id: int) -> dict[str, Any]:
        experiment = self._repository.get_experiment(experiment_id)
        if experiment is None:
            raise BizError(ErrorCode.NOT_FOUND, "Experiment not found")
        cases = self._repository.list_cases(int(experiment["eval_set_id"]))
        if not cases:
            raise BizError(ErrorCode.BAD_REQUEST, "Eval set has no cases")
        evaluators = [self._require_evaluator(evaluator_id) for evaluator_id in list(experiment["evaluator_ids"] or [])]
        run = self._repository.create_run(experiment_id, len(cases))
        case_results: list[dict[str, Any]] = []
        for eval_case in cases:
            case_results.append(self._execute_case(int(run["id"]), experiment, eval_case, evaluators))
        finished = self._finish_run_from_case_results(int(run["id"]), case_results)
        self._repository.update_experiment_latest_run(experiment_id, int(run["id"]))
        if finished is None:
            raise BizError(ErrorCode.NOT_FOUND, "Run not found")
        return self._run_response(finished, case_results).model_dump(by_alias=True)

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
        evaluators = [self._require_evaluator(evaluator_id) for evaluator_id in list(experiment["evaluator_ids"] or [])]
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

    def _experiment_response(self, row: dict[str, Any]) -> ExperimentResponse:
        return ExperimentResponse(
            id=int(row["id"]),
            name=row["name"],
            targetType=row["target_type"],
            targetId=int(row["target_id"]),
            evalSetId=int(row["eval_set_id"]),
            evaluatorIds=[int(item) for item in list(row["evaluator_ids"] or [])],
            status=row["status"],
            latestRunId=int(row["latest_run_id"]) if row["latest_run_id"] is not None else None,
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

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
        target_output = self._run_target(
            str(experiment["target_type"]),
            int(experiment["target_id"]),
            str(eval_case["input"]),
        )
        evaluator_results = [
            self._evaluate_case(evaluator, str(eval_case["expected_output"]), target_output)
            for evaluator in evaluators
        ]
        score = sum(float(result["score"]) for result in evaluator_results) / len(evaluator_results)
        passed = all(bool(result["passed"]) for result in evaluator_results)
        return self._repository.create_case_result(
            {
                "run_id": run_id,
                "eval_case_id": int(eval_case["id"]),
                "input": eval_case["input"],
                "expected_output": eval_case["expected_output"],
                "target_output": target_output,
                "status": "PASSED" if passed else "FAILED",
                "score": round(score, 4),
                "evaluator_results": evaluator_results,
                "reason": "; ".join(str(result["reason"]) for result in evaluator_results),
            }
        )

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

    def _run_agent_target(self, agent_id: int, content: str) -> str:
        session = self._repository.session
        chat_service = ChatService(
            ChatRepository(session),
            knowledge_facade=KnowledgeFacade(session),
            workflow_facade=WorkflowFacade(session),
            mcp_facade=McpFacade(session),
            model_facade=ProviderModelFacade(session),
        )
        chat_session = chat_service.create_session(ChatSessionCreateRequest(agentId=agent_id))
        turn = chat_service.send_message(
            int(chat_session["id"]),
            ChatMessageCreateRequest(content=content, stream=False),
        )
        return str(turn["assistantMessage"]["content"])

    def _run_target(self, target_type: str, target_id: int, content: str) -> str:
        if target_type == "AGENT":
            return self._run_agent_target(target_id, content)
        if target_type in {"WORKFLOW", "CHATFLOW"}:
            self._validate_target(target_type, target_id)
            output = WorkflowFacade(self._repository.session).execute_for_chat(target_id, content)
            return "" if output is None else str(output)
        raise BizError(ErrorCode.BAD_REQUEST, "Unsupported evaluation target type")

    def _evaluate_llm_judge(
        self,
        config: dict[str, Any],
        expected_output: str,
        actual_output: str,
    ) -> EvaluationSampleResult:
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
        prompt = (
            "LLM_JUDGE_EVALUATION\n"
            "Return strict JSON with keys passed, score, reason.\n\n"
            f"Expected output:\n{expected_output}\n\n"
            f"Actual output:\n{actual_output}\n\n"
            f"Rubric:\n{config.get('rubric') or ''}\n"
        )
        payload = {
            "model": model_config.model_id,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 300,
        }
        raw = client.complete(payload)
        content = str(raw.get("choices", [{}])[0].get("message", {}).get("content") or "")
        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, "LLM Judge response is not valid JSON") from exc
        score = float(parsed.get("score") or 0.0)
        passed = bool(parsed.get("passed")) and score >= float(config.get("passingScore") or 0.7)
        return EvaluationSampleResult(
            passed=passed,
            score=round(score, 4),
            reason=str(parsed.get("reason") or ""),
        )


def _normalize_tags(tags: list[str]) -> list[str]:
    normalized: list[str] = []
    for tag in tags:
        value = tag.strip()
        if value and value not in normalized:
            normalized.append(value)
    return normalized
