from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.modules.agent.infra.repository import AgentRepository
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.provider.api.facade import ProviderModelFacade
from app.modules.provider.api.schemas import ModelConfigDto
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser
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

LlmClientFactory = Callable[[ProviderChatConfig], Any]


class WorkflowService:
    def __init__(
        self,
        repository: WorkflowRepository,
        flow_type: str = "WORKFLOW",
        agent_repository: AgentRepository | None = None,
        model_facade: ProviderModelFacade | None = None,
        request_builder: OpenAIChatRequestBuilder | None = None,
        parser: OpenAIAdapterParser | None = None,
        llm_client_factory: LlmClientFactory | None = None,
    ) -> None:
        self._repository = repository
        self._flow_type = flow_type
        self._agent_repository = agent_repository
        self._model_facade = model_facade
        self._request_builder = request_builder or OpenAIChatRequestBuilder()
        self._parser = parser or OpenAIAdapterParser()
        self._llm_client_factory = llm_client_factory or ProviderBackedOpenAIChatClient

    def list(self, page: int, page_size: int, status: str | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, status, self._flow_type)
        response = WorkflowPageResponse(
            list=[self._response(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def create(self, request: WorkflowCreateRequest) -> dict[str, Any]:
        row = self._repository.create(
            {"name": request.name, "description": request.description, "flow_type": self._flow_type},
            [node.model_dump() for node in request.nodes],
            [edge.model_dump() for edge in request.edges],
        )
        return self._detail_response(row).model_dump(by_alias=True)

    def get(self, workflow_id: int) -> dict[str, Any]:
        row = self._repository.get(workflow_id, self._flow_type)
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
            self._flow_type,
        )
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        return self._detail_response(row).model_dump(by_alias=True)

    def delete(self, workflow_id: int) -> None:
        if not self._repository.delete(workflow_id, self._flow_type):
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")

    def execute(self, workflow_id: int, request: WorkflowRunRequest) -> dict[str, Any]:
        if self._repository.get(workflow_id, self._flow_type) is None:
            raise BizError(ErrorCode.NOT_FOUND, "Workflow not found")
        try:
            result = WorkflowExecutionEngine(
                self._repository,
                llm_completer=self._llm_completer(workflow_id),
            ).run(workflow_id, dict(request.input))
        except WorkflowExecutionError as exc:
            raise BizError(ErrorCode.BAD_REQUEST, str(exc)) from exc
        response = WorkflowRunResponse(
            runId=result.run_id,
            status=result.status,
            output=result.output,
        )
        return response.model_dump(by_alias=True)

    def _llm_completer(self, workflow_id: int) -> _AgentBackedWorkflowLlmCompleter | None:
        nodes = self._repository.list_nodes(workflow_id)
        if not any(node["type"] == "LLM" for node in nodes):
            return None
        if self._agent_repository is None or self._model_facade is None:
            return None
        agent = self._agent_repository.find_default_live_llm_agent()
        if agent is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow LLM agent is not configured")
        model_config = self._model_facade.get_enabled_model_config(int(agent["model_config_id"]))
        if model_config.provider_base_url.startswith("mock://"):
            raise BizError(ErrorCode.BAD_REQUEST, "Workflow LLM agent must use a real provider")
        return _AgentBackedWorkflowLlmCompleter(
            agent=agent,
            model_config=model_config,
            request_builder=self._request_builder,
            parser=self._parser,
            llm_client_factory=self._llm_client_factory,
        )

    def _response(self, row: dict[str, Any]) -> WorkflowResponse:
        return WorkflowResponse(
            id=int(row["id"]),
            name=row["name"],
            description=row["description"] or "",
            flowType=row.get("flow_type") or "WORKFLOW",
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


class _AgentBackedWorkflowLlmCompleter:
    def __init__(
        self,
        agent: dict[str, Any],
        model_config: ModelConfigDto,
        request_builder: OpenAIChatRequestBuilder,
        parser: OpenAIAdapterParser,
        llm_client_factory: LlmClientFactory,
    ) -> None:
        self._agent = agent
        self._model_config = model_config
        self._request_builder = request_builder
        self._parser = parser
        self._llm_client_factory = llm_client_factory

    def complete_prompt(self, prompt: str) -> str:
        payload = self._request_builder.build(
            model=self._model_config.model_id,
            messages=self._messages(prompt),
            temperature=float(self._agent["temperature"]),
            max_tokens=int(self._agent["max_tokens"]),
            extra_params=self._model_config.extra_params,
        )
        result = self._parser.parse_chat_response(self._llm_client().complete(payload))
        return result.content

    def _messages(self, prompt: str) -> list[ChatRequestMessage]:
        messages: list[ChatRequestMessage] = []
        system_prompt = str(self._agent.get("system_prompt") or "")
        if system_prompt:
            messages.append(ChatRequestMessage(role="system", content=system_prompt))
        messages.append(ChatRequestMessage(role="user", content=prompt))
        return messages

    def _llm_client(self) -> Any:
        return self._llm_client_factory(
            ProviderChatConfig(
                provider_type=self._model_config.provider_type,
                base_url=self._model_config.provider_base_url,
                auth_config=self._model_config.provider_auth_config,
            )
        )
