from __future__ import annotations

from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.workflow.domain.engine import WorkflowExecutionEngine, WorkflowExecutionError
from app.modules.workflow.infra.repository import WorkflowRepository
from app.modules.workflow.web.schemas import (
    WorkflowCreateRequest,
    WorkflowDetailResponse,
    WorkflowEdgeResponse,
    WorkflowNodeResponse,
    WorkflowPageResponse,
    WorkflowRunRequest,
    WorkflowRunResponse,
    WorkflowResponse,
    WorkflowUpdateRequest,
    format_datetime,
)


class WorkflowService:
    def __init__(self, repository: WorkflowRepository) -> None:
        self._repository = repository

    def list(self, page: int, page_size: int, status: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, status)
        response = WorkflowPageResponse(
            list=[self._response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create(self, request: WorkflowCreateRequest) -> dict[str, Any]:
        row = self._repository.create(
            {"name": request.name, "description": request.description},
            [node.model_dump() for node in request.nodes],
            [edge.model_dump() for edge in request.edges],
        )
        return self._detail_response(row).model_dump(by_alias=True)

    def get(self, workflow_id: int) -> dict[str, Any]:
        row = self._repository.get(workflow_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        return self._detail_response(row).model_dump(by_alias=True)

    def update(self, workflow_id: int, request: WorkflowUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if request.name is not None:
            values["name"] = request.name
        if request.description is not None:
            values["description"] = request.description
        if request.status is not None:
            values["status"] = request.status
        row = self._repository.update(
            workflow_id,
            values,
            [node.model_dump() for node in request.nodes] if request.nodes is not None else None,
            [edge.model_dump() for edge in request.edges] if request.edges is not None else None,
        )
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        return self._detail_response(row).model_dump(by_alias=True)

    def delete(self, workflow_id: int) -> None:
        if not self._repository.delete(workflow_id):
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")

    def execute(self, workflow_id: int, request: WorkflowRunRequest) -> dict[str, Any]:
        try:
            result = WorkflowExecutionEngine(self._repository).run(workflow_id, dict(request.input))
        except WorkflowExecutionError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        response = WorkflowRunResponse(
            runId=result.run_id,
            status=result.status,
            output=result.output,
        )
        return response.model_dump(by_alias=True)

    def _response(self, row: dict[str, Any]) -> WorkflowResponse:
        return WorkflowResponse(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            status=row["status"],
            createdAt=format_datetime(row["created_at"]),
            updatedAt=format_datetime(row["updated_at"]),
        )

    def _detail_response(self, row: dict[str, Any]) -> WorkflowDetailResponse:
        workflow_id = int(row["id"])
        return WorkflowDetailResponse(
            **self._response(row).model_dump(by_alias=True),
            nodes=[
                WorkflowNodeResponse(
                    nodeKey=node["node_key"],
                    type=node["type"],
                    name=node["name"] or "",
                    config=node["config"] or {},
                )
                for node in self._repository.list_nodes(workflow_id)
            ],
            edges=[
                WorkflowEdgeResponse(
                    sourceNodeKey=edge["source_node_key"],
                    targetNodeKey=edge["target_node_key"],
                    condition=edge["condition_expr"],
                )
                for edge in self._repository.list_edges(workflow_id)
            ],
        )
