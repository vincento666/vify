from typing import Any

from fastapi import APIRouter, Depends, File, Query, Response, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_session
from app.core.responses import success
from app.modules.evaluation.domain.service import EvaluationService
from app.modules.evaluation.infra.repository import EvaluationRepository
from app.modules.evaluation.web.schemas import (
    EvalCaseCreateRequest,
    EvalCaseUpdateRequest,
    EvalSetCreateRequest,
    EvalSetUpdateRequest,
    ExperimentCreateRequest,
    EvaluatorCreateRequest,
    EvaluatorDraftTestRequest,
    EvaluatorSampleTestRequest,
    EvaluatorUpdateRequest,
)

router = APIRouter(prefix="/api/v1/eval-sets", tags=["eval-sets"])
case_router = APIRouter(prefix="/api/v1/eval-cases", tags=["eval-cases"])
evaluator_router = APIRouter(prefix="/api/v1/evaluators", tags=["evaluators"])
experiment_router = APIRouter(prefix="/api/v1/evaluation-experiments", tags=["evaluation-experiments"])
run_router = APIRouter(prefix="/api/v1/evaluation-runs", tags=["evaluation-runs"])


def get_evaluation_service(session: Session = Depends(get_session)) -> EvaluationService:
    return EvaluationService(EvaluationRepository(session))


@router.get("")
def list_eval_sets(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    name: str | None = None,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.list_eval_sets(page, page_size, name))


@router.post("")
def create_eval_set(
    request: EvalSetCreateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.create_eval_set(request))


@router.get("/{eval_set_id}")
def get_eval_set(
    eval_set_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.get_eval_set(eval_set_id))


@router.put("/{eval_set_id}")
def update_eval_set(
    eval_set_id: int,
    request: EvalSetUpdateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.update_eval_set(eval_set_id, request))


@router.delete("/{eval_set_id}")
def delete_eval_set(
    eval_set_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    service.delete_eval_set(eval_set_id)
    return success(None)


@router.post("/{eval_set_id}/cases")
def create_case(
    eval_set_id: int,
    request: EvalCaseCreateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.create_case(eval_set_id, request))


@router.post("/{eval_set_id}/cases/import-csv")
async def import_cases_csv(
    eval_set_id: int,
    file: UploadFile = File(...),
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    content = await file.read()
    return success(service.import_cases_csv(eval_set_id, content))


@case_router.put("/{eval_case_id}")
def update_case(
    eval_case_id: int,
    request: EvalCaseUpdateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.update_case(eval_case_id, request))


@case_router.delete("/{eval_case_id}")
def delete_case(
    eval_case_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    service.delete_case(eval_case_id)
    return success(None)


@evaluator_router.get("")
def list_evaluators(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    name: str | None = None,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.list_evaluators(page, page_size, name))


@evaluator_router.post("")
def create_evaluator(
    request: EvaluatorCreateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.create_evaluator(request))


@evaluator_router.post("/test")
def test_draft_evaluator(
    request: EvaluatorDraftTestRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.test_draft_evaluator(request))


@evaluator_router.get("/{evaluator_id}")
def get_evaluator(
    evaluator_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.get_evaluator(evaluator_id))


@evaluator_router.put("/{evaluator_id}")
def update_evaluator(
    evaluator_id: int,
    request: EvaluatorUpdateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.update_evaluator(evaluator_id, request))


@evaluator_router.delete("/{evaluator_id}")
def delete_evaluator(
    evaluator_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    service.delete_evaluator(evaluator_id)
    return success(None)


@evaluator_router.post("/{evaluator_id}/test")
def test_evaluator(
    evaluator_id: int,
    request: EvaluatorSampleTestRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.test_evaluator(evaluator_id, request))


@experiment_router.get("")
def list_experiments(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    name: str | None = None,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.list_experiments(page, page_size, name))


@experiment_router.post("")
def create_experiment(
    request: ExperimentCreateRequest,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.create_experiment(request))


@experiment_router.post("/{experiment_id}/runs")
def run_experiment(
    experiment_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.run_experiment(experiment_id))


@run_router.get("")
def list_runs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100, alias="pageSize"),
    status: str | None = None,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.list_runs(page, page_size, status))


@run_router.get("/compare")
def compare_runs(
    base_run_id: int = Query(..., alias="baseRunId"),
    candidate_run_id: int = Query(..., alias="candidateRunId"),
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.compare_runs(base_run_id, candidate_run_id))


@run_router.get("/{run_id}")
def get_run_detail(
    run_id: int,
    case_status: str | None = Query(None, alias="caseStatus"),
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.get_run_detail(run_id, case_status))


@run_router.post("/{run_id}/case-results/{case_result_id}/rerun")
def rerun_case_result(
    run_id: int,
    case_result_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> dict[str, Any]:
    return success(service.rerun_case_result(run_id, case_result_id))


@run_router.get("/{run_id}/export-csv")
def export_run_csv(
    run_id: int,
    service: EvaluationService = Depends(get_evaluation_service),
) -> Response:
    content = service.export_run_csv(run_id)
    return Response(
        content=content,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="evaluation-run-{run_id}.csv"'},
    )
