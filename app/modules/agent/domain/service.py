from __future__ import annotations

import re
from typing import Any

from app.core.errors import BizError, ErrorCode
from app.core.host.context import RequestContext
from app.modules.audit.infra.repository import AuditRepository
from app.modules.agent.infra.repository import AgentRepository
from app.modules.agent.web.schemas import (
    AgentCreateRequest,
    AgentListPage,
    AgentPublishCreateRequest,
    AgentPromptOptimizationRequest,
    AgentUpdateRequest,
    AgentVersionCreateRequest,
)
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)
from app.modules.provider.infra.llm_adapters import OpenAIAdapterParser
from app.modules.provider.api.facade import ProviderModelFacade

_VARIABLE_NAME_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_VARIABLE_TYPES = {"string", "number", "boolean", "json"}


class AgentService:
    def __init__(
        self,
        repository: AgentRepository,
        model_facade: ProviderModelFacade,
        audit_repository: AuditRepository | None = None,
        request_context: RequestContext | None = None,
    ) -> None:
        self._repository = repository
        self._model_facade = model_facade
        self._audit_repository = audit_repository
        self._request_context = request_context

    def create(self, request: AgentCreateRequest) -> dict[str, Any]:
        self._validate_model(request.model_config_id)
        tool_ids = self._dedupe_tool_ids(request.tool_ids)
        self._validate_tool_ids(tool_ids)
        row = self._repository.create(self._values_from_create(request))
        self._repository.replace_tool_bindings(int(row["id"]), tool_ids)
        self._audit("AGENT_CREATE", int(row["id"]), {"name": row["name"]})
        return self._detail(row)

    def list_agents(self, page: int, page_size: int, enabled: bool | None) -> dict[str, Any]:
        rows, total = self._repository.list_page(page, page_size, enabled)
        response = AgentListPage(
            list=[self._list_item(row) for row in rows],
            total=total,
            page=page,
            pageSize=page_size,
        )
        return response.model_dump(by_alias=True)

    def get(self, agent_id: int) -> dict[str, Any]:
        row = self._repository.get(agent_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
        return self._detail(row)

    def update(self, agent_id: int, request: AgentUpdateRequest) -> dict[str, Any]:
        self._validate_model(request.model_config_id)
        row = self._repository.update(agent_id, self._values_from_update(request))
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
        self._audit("AGENT_UPDATE", agent_id, {"name": row["name"]})
        return self._detail(row)

    def delete(self, agent_id: int) -> None:
        if not self._repository.delete(agent_id):
            raise BizError(ErrorCode.NOT_FOUND, "Agent not found")
        self._audit("AGENT_DELETE", agent_id, {})

    def replace_tools(self, agent_id: int, tool_ids: list[int]) -> None:
        self.get(agent_id)
        deduped_tool_ids = self._dedupe_tool_ids(tool_ids)
        self._validate_tool_ids(deduped_tool_ids)
        self._repository.replace_tool_bindings(agent_id, deduped_tool_ids)
        self._audit("AGENT_TOOL_BINDING_UPDATE", agent_id, {"toolIds": deduped_tool_ids})

    def create_version(self, agent_id: int, request: AgentVersionCreateRequest) -> dict[str, Any]:
        detail = self.get(agent_id)
        name = request.name.strip() or f"Version {self._repository.next_version_no(agent_id)}"
        row = self._repository.create_version(agent_id, name, self._snapshot_from_detail(detail))
        self._audit("AGENT_VERSION_CREATE", agent_id, {"versionId": int(row["id"]), "name": row["name"]})
        return self._version_detail(row)

    def list_versions(self, agent_id: int) -> dict[str, Any]:
        self.get(agent_id)
        versions = [self._version_detail(row) for row in self._repository.list_versions(agent_id)]
        latest = versions[0]["id"] if versions else None
        released = next((version["id"] for version in versions if version["released"]), None)
        return {
            "list": versions,
            "latestVersionId": latest,
            "releasedVersionId": released,
        }

    def release_version(self, agent_id: int, version_id: int) -> dict[str, Any]:
        detail = self.get(agent_id)
        self._assert_evaluation_gate(detail)
        row = self._repository.release_version(agent_id, version_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent version not found")
        self._audit("AGENT_VERSION_RELEASE", agent_id, {"versionId": version_id})
        return self._version_detail(row)

    def publish(self, agent_id: int, request: AgentPublishCreateRequest) -> dict[str, Any]:
        self.get(agent_id)
        version = self._repository.get_version(agent_id, request.version_id)
        if version is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent version not found")
        if not version["released"]:
            raise BizError(ErrorCode.BAD_REQUEST, "Only released Agent versions can be published")
        channel_type = request.channel_type.strip().upper() or "API"
        endpoint = self._publish_endpoint(agent_id, request.version_id, channel_type)
        row = self._repository.create_publish_record(
            agent_id=agent_id,
            version_id=request.version_id,
            channel_type=channel_type,
            endpoint=endpoint,
            config=request.config,
        )
        self._audit(
            "AGENT_PUBLISH",
            agent_id,
            {"publishId": int(row["id"]), "versionId": request.version_id, "channelType": channel_type},
        )
        return self._publish_detail(row)

    def list_publishes(self, agent_id: int) -> dict[str, Any]:
        self.get(agent_id)
        return {"list": [self._publish_detail(row) for row in self._repository.list_publish_records(agent_id)]}

    def unpublish(self, agent_id: int, publish_id: int) -> dict[str, Any]:
        self.get(agent_id)
        row = self._repository.unpublish_record(agent_id, publish_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "Agent publish record not found")
        self._audit("AGENT_UNPUBLISH", agent_id, {"publishId": publish_id})
        return self._publish_detail(row)

    def optimize_prompt(self, agent_id: int, request: AgentPromptOptimizationRequest) -> dict[str, Any]:
        detail = self.get(agent_id)
        instruction = request.instruction.strip() or "Improve clarity, safety, and task specificity."
        original_prompt = detail["systemPrompt"] or ""
        model_config = self._model_facade.get_enabled_model_config(int(detail["modelConfigId"]))
        user_prompt = (
            "Improve this Agent system prompt. Return only the optimized prompt text.\n\n"
            f"Current prompt:\n{original_prompt or '(empty)'}\n\n"
            f"Optimization instruction:\n{instruction}"
        )
        request_builder = OpenAIChatRequestBuilder()
        payload = request_builder.build(
            model=model_config.model_id,
            messages=[
                ChatRequestMessage(
                    role="system",
                    content="You improve AI agent system prompts while preserving the original product intent.",
                ),
                ChatRequestMessage(role="user", content=user_prompt),
            ],
            temperature=0.2,
            max_tokens=min(max(int(detail["maxTokens"]), 1), 2048),
            extra_params=model_config.extra_params,
        )
        client = ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type=model_config.provider_type,
                base_url=model_config.provider_base_url,
                auth_config=model_config.provider_auth_config,
            )
        )
        result = OpenAIAdapterParser().parse_chat_response(client.complete(payload))
        optimized_prompt = (result.content or "").strip() or original_prompt
        audit = {
            "modelConfigId": int(detail["modelConfigId"]),
            "modelId": model_config.model_id,
            "instruction": instruction,
            "tokenEstimate": max(1, len(user_prompt.split()) + len(optimized_prompt.split())),
            "finishReason": result.finish_reason or "",
        }
        row = self._repository.create_prompt_optimization(
            agent_id=agent_id,
            original_prompt=original_prompt,
            instruction=instruction,
            optimized_prompt=optimized_prompt,
            model_config_id=int(detail["modelConfigId"]),
            audit=audit,
        )
        self._audit("AGENT_PROMPT_OPTIMIZE", agent_id, {"optimizationId": int(row["id"]), **audit})
        return self._prompt_optimization_detail(row)

    def list_prompt_optimizations(self, agent_id: int) -> dict[str, Any]:
        self.get(agent_id)
        return {
            "list": [
                self._prompt_optimization_detail(row)
                for row in self._repository.list_prompt_optimizations(agent_id)
            ]
        }

    def _audit(self, action: str, agent_id: int, metadata: dict[str, Any]) -> None:
        if self._audit_repository is None:
            return
        self._audit_repository.record(
            action=action,
            resource_type="AGENT",
            resource_id=agent_id,
            status="succeeded",
            metadata=metadata,
            request_context=self._request_context,
        )

    def _values_from_create(self, request: AgentCreateRequest) -> dict[str, Any]:
        return {
            "name": request.name,
            "description": request.description,
            "system_prompt": request.system_prompt,
            "opening_message": request.opening_message.strip(),
            "suggested_questions": self._normalize_suggested_questions(request.suggested_questions),
            "variables": self._normalize_variables(request.variables),
            "memory": self._normalize_memory(request.memory),
            "tool_policies": self._normalize_tool_policies(request.tool_policies),
            "model_config_id": request.model_config_id,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "max_context_turns": request.max_context_turns,
            "knowledge_base_id": request.knowledge_base_id,
            "knowledge_base_ids": self._normalize_knowledge_base_ids(request.knowledge_base_id, request.knowledge_base_ids),
            "retrieval_settings": self._normalize_retrieval_settings(request.retrieval_settings),
            "evaluation_gate": self._normalize_evaluation_gate(request.evaluation_gate),
            "access": self._normalize_shell_config(request.access),
            "sharing": self._normalize_shell_config(request.sharing),
            "catalog": self._normalize_shell_config(request.catalog),
            "analytics": self._normalize_shell_config(request.analytics),
            "workflow_id": request.workflow_id,
        }

    def _validate_model(self, model_config_id: int) -> None:
        self._model_facade.get_enabled_model_config(model_config_id)

    def _dedupe_tool_ids(self, tool_ids: list[int]) -> list[int]:
        seen: set[int] = set()
        deduped: list[int] = []
        for tool_id in tool_ids:
            if tool_id in seen:
                continue
            seen.add(tool_id)
            deduped.append(tool_id)
        return deduped

    def _validate_tool_ids(self, tool_ids: list[int]) -> None:
        if not tool_ids:
            return
        available = set(self._repository.list_available_tool_ids(tool_ids))
        missing = [tool_id for tool_id in tool_ids if tool_id not in available]
        if missing:
            raise BizError(ErrorCode.VALIDATION_ERROR, f"MCP server not available: {missing[0]}")

    def _values_from_update(self, request: AgentUpdateRequest) -> dict[str, Any]:
        return {
            "name": request.name,
            "description": request.description,
            "system_prompt": request.system_prompt,
            "opening_message": request.opening_message.strip(),
            "suggested_questions": self._normalize_suggested_questions(request.suggested_questions),
            "variables": self._normalize_variables(request.variables),
            "memory": self._normalize_memory(request.memory),
            "tool_policies": self._normalize_tool_policies(request.tool_policies),
            "model_config_id": request.model_config_id,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
            "max_context_turns": request.max_context_turns,
            "knowledge_base_id": request.knowledge_base_id,
            "knowledge_base_ids": self._normalize_knowledge_base_ids(request.knowledge_base_id, request.knowledge_base_ids),
            "retrieval_settings": self._normalize_retrieval_settings(request.retrieval_settings),
            "evaluation_gate": self._normalize_evaluation_gate(request.evaluation_gate),
            "access": self._normalize_shell_config(request.access),
            "sharing": self._normalize_shell_config(request.sharing),
            "catalog": self._normalize_shell_config(request.catalog),
            "analytics": self._normalize_shell_config(request.analytics),
            "workflow_id": request.workflow_id,
        }

    def _detail(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "description": row["description"] or "",
            "systemPrompt": row["system_prompt"] or "",
            "openingMessage": row.get("opening_message") or "",
            "suggestedQuestions": self._normalize_suggested_questions(row.get("suggested_questions")),
            "variables": self._normalize_variables(row.get("variables")),
            "memory": self._normalize_memory(row.get("memory")),
            "toolPolicies": self._normalize_tool_policies(row.get("tool_policies")),
            "modelConfigId": int(row["model_config_id"]),
            "temperature": float(row["temperature"]),
            "maxTokens": int(row["max_tokens"]),
            "maxContextTurns": int(row["max_context_turns"]),
            "enabled": 1 if row["enabled"] else 0,
            "toolIds": self._repository.list_tool_ids(int(row["id"])),
            "knowledgeBaseId": row.get("knowledge_base_id"),
            "knowledgeBaseIds": self._normalize_knowledge_base_ids(row.get("knowledge_base_id"), row.get("knowledge_base_ids")),
            "retrievalSettings": self._normalize_retrieval_settings(row.get("retrieval_settings")),
            "evaluationGate": self._normalize_evaluation_gate(row.get("evaluation_gate")),
            "access": self._normalize_shell_config(row.get("access")),
            "sharing": self._normalize_shell_config(row.get("sharing")),
            "catalog": self._normalize_shell_config(row.get("catalog")),
            "analytics": self._normalize_shell_config(row.get("analytics")),
            "workflowId": row.get("workflow_id"),
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }

    def _snapshot_from_detail(self, detail: dict[str, Any]) -> dict[str, Any]:
        return {
            "name": detail["name"],
            "description": detail["description"],
            "systemPrompt": detail["systemPrompt"],
            "openingMessage": detail["openingMessage"],
            "suggestedQuestions": detail["suggestedQuestions"],
            "variables": detail["variables"],
            "memory": detail["memory"],
            "toolPolicies": detail["toolPolicies"],
            "modelConfigId": detail["modelConfigId"],
            "temperature": detail["temperature"],
            "maxTokens": detail["maxTokens"],
            "maxContextTurns": detail["maxContextTurns"],
            "toolIds": detail["toolIds"],
            "knowledgeBaseId": detail["knowledgeBaseId"],
            "knowledgeBaseIds": detail["knowledgeBaseIds"],
            "retrievalSettings": detail["retrievalSettings"],
            "evaluationGate": detail["evaluationGate"],
            "access": detail["access"],
            "sharing": detail["sharing"],
            "catalog": detail["catalog"],
            "analytics": detail["analytics"],
            "workflowId": detail["workflowId"],
        }

    def _version_detail(self, row: dict[str, Any]) -> dict[str, Any]:
        released_at = row.get("released_at")
        return {
            "id": int(row["id"]),
            "agentId": int(row["agent_id"]),
            "versionNo": int(row["version_no"]),
            "name": row["name"] or "",
            "snapshot": row["snapshot"] or {},
            "released": bool(row["released"]),
            "releasedAt": released_at.isoformat() if released_at else None,
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }

    def _publish_endpoint(self, agent_id: int, version_id: int, channel_type: str) -> str:
        if channel_type == "API":
            return f"/api/public/agents/{agent_id}/versions/{version_id}/chat"
        return f"channel://{channel_type.lower()}/agents/{agent_id}/versions/{version_id}"

    def _publish_detail(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "agentId": int(row["agent_id"]),
            "versionId": int(row["version_id"]),
            "channelType": row["channel_type"],
            "status": row["status"],
            "endpoint": row["endpoint"],
            "config": row.get("config") or {},
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }

    def _prompt_optimization_detail(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "agentId": int(row["agent_id"]),
            "originalPrompt": row["original_prompt"] or "",
            "instruction": row["instruction"] or "",
            "optimizedPrompt": row["optimized_prompt"] or "",
            "modelConfigId": int(row["model_config_id"]),
            "audit": row.get("audit") or {},
            "createdAt": row["created_at"].isoformat(),
            "updatedAt": row["updated_at"].isoformat(),
        }

    def _list_item(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": row["name"],
            "description": row["description"] or "",
            "openingMessage": row.get("opening_message") or "",
            "suggestedQuestions": self._normalize_suggested_questions(row.get("suggested_questions")),
            "variables": self._normalize_variables(row.get("variables")),
            "memory": self._normalize_memory(row.get("memory")),
            "toolPolicies": self._normalize_tool_policies(row.get("tool_policies")),
            "modelConfigId": int(row["model_config_id"]),
            "temperature": float(row["temperature"]),
            "enabled": 1 if row["enabled"] else 0,
            "toolCount": self._repository.tool_count(int(row["id"])),
            "workflowId": row.get("workflow_id"),
            "knowledgeBaseId": row.get("knowledge_base_id"),
            "knowledgeBaseIds": self._normalize_knowledge_base_ids(row.get("knowledge_base_id"), row.get("knowledge_base_ids")),
            "retrievalSettings": self._normalize_retrieval_settings(row.get("retrieval_settings")),
            "evaluationGate": self._normalize_evaluation_gate(row.get("evaluation_gate")),
            "access": self._normalize_shell_config(row.get("access")),
            "sharing": self._normalize_shell_config(row.get("sharing")),
            "catalog": self._normalize_shell_config(row.get("catalog")),
            "analytics": self._normalize_shell_config(row.get("analytics")),
            "createdAt": row["created_at"].isoformat(),
        }

    def _normalize_suggested_questions(self, questions: Any) -> list[str]:
        if not isinstance(questions, list):
            return []
        normalized: list[str] = []
        seen: set[str] = set()
        for question in questions:
            value = str(question).strip()
            if not value or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _normalize_variables(self, variables: Any) -> list[dict[str, Any]]:
        if not isinstance(variables, list):
            return []
        normalized: list[dict[str, Any]] = []
        seen: set[str] = set()
        for raw_variable in variables:
            if not isinstance(raw_variable, dict):
                raise BizError(ErrorCode.BAD_REQUEST, "Agent variables must be objects")
            name = str(raw_variable.get("name") or "").strip()
            if not name or not _VARIABLE_NAME_PATTERN.match(name):
                raise BizError(ErrorCode.BAD_REQUEST, f"Invalid Agent variable name: {name or '<empty>'}")
            if name in seen:
                raise BizError(ErrorCode.BAD_REQUEST, f"Duplicate Agent variable name: {name}")
            variable_type = str(raw_variable.get("type") or "string").strip().lower()
            if variable_type not in _VARIABLE_TYPES:
                raise BizError(ErrorCode.BAD_REQUEST, f"Unsupported Agent variable type: {variable_type}")
            seen.add(name)
            normalized.append(
                {
                    "name": name,
                    "type": variable_type,
                    "defaultValue": raw_variable.get("defaultValue"),
                    "required": bool(raw_variable.get("required", False)),
                    "description": str(raw_variable.get("description") or "").strip(),
                }
            )
        return normalized

    def _normalize_memory(self, memory: Any) -> dict[str, Any]:
        if not isinstance(memory, dict):
            return {}
        normalized: dict[str, Any] = {}
        for raw_key, raw_value in memory.items():
            key = str(raw_key or "").strip()
            if not key:
                continue
            normalized[key] = raw_value
        return normalized

    def _normalize_tool_policies(self, policies: Any) -> dict[str, dict[str, Any]]:
        if not isinstance(policies, dict):
            return {}
        normalized: dict[str, dict[str, Any]] = {}
        for raw_name, raw_policy in policies.items():
            name = str(raw_name or "").strip()
            if not name or not isinstance(raw_policy, dict):
                continue
            try:
                timeout_ms = int(raw_policy.get("timeoutMs") or 30_000)
            except (TypeError, ValueError):
                timeout_ms = 30_000
            argument_presets = raw_policy.get("argumentPresets")
            normalized[name] = {
                "enabled": bool(raw_policy.get("enabled", True)),
                "callMode": str(raw_policy.get("callMode") or "auto"),
                "argumentPresets": argument_presets if isinstance(argument_presets, dict) else {},
                "approvalRequired": bool(raw_policy.get("approvalRequired", False)),
                "timeoutMs": max(1, timeout_ms),
                "failureBehavior": str(raw_policy.get("failureBehavior") or "return_error"),
            }
        return normalized

    def _normalize_knowledge_base_ids(self, primary_id: Any, ids: Any) -> list[int]:
        raw_ids: list[Any] = []
        if primary_id is not None:
            raw_ids.append(primary_id)
        if isinstance(ids, list):
            raw_ids.extend(ids)
        normalized: list[int] = []
        seen: set[int] = set()
        for raw_id in raw_ids:
            try:
                value = int(raw_id)
            except (TypeError, ValueError):
                continue
            if value <= 0 or value in seen:
                continue
            seen.add(value)
            normalized.append(value)
        return normalized

    def _normalize_retrieval_settings(self, settings: Any) -> dict[str, Any]:
        if not isinstance(settings, dict):
            settings = {}
        try:
            top_k = int(settings.get("topK") or 3)
        except (TypeError, ValueError):
            top_k = 3
        try:
            threshold = float(settings.get("scoreThreshold") or 0)
        except (TypeError, ValueError):
            threshold = 0.0
        return {
            "topK": min(max(top_k, 1), 20),
            "scoreThreshold": min(max(threshold, 0.0), 1.0),
            "retrievalMode": self._normalize_retrieval_mode(settings.get("retrievalMode")),
            "rerank": bool(settings.get("rerank", False)),
            "citationStyle": str(settings.get("citationStyle") or "numbered"),
        }

    def _normalize_retrieval_mode(self, value: Any) -> str:
        normalized = str(value or "auto").strip().lower()
        if normalized in {"auto", "hybrid", "semantic", "keyword", "faq"}:
            return normalized
        return "auto"

    def _normalize_evaluation_gate(self, gate: Any) -> dict[str, Any]:
        if not isinstance(gate, dict):
            return {"enabled": False, "experimentId": None, "requiredPassRate": 1.0}
        experiment_id = gate.get("experimentId")
        try:
            experiment_id = int(experiment_id) if experiment_id is not None else None
        except (TypeError, ValueError):
            experiment_id = None
        try:
            required_pass_rate = float(gate.get("requiredPassRate") or 1.0)
        except (TypeError, ValueError):
            required_pass_rate = 1.0
        return {
            "enabled": bool(gate.get("enabled", False)),
            "experimentId": experiment_id,
            "requiredPassRate": min(max(required_pass_rate, 0.0), 1.0),
        }

    def _assert_evaluation_gate(self, detail: dict[str, Any]) -> None:
        gate = self._normalize_evaluation_gate(detail.get("evaluationGate"))
        if not gate["enabled"]:
            return
        experiment_id = gate.get("experimentId")
        if not experiment_id:
            raise BizError(ErrorCode.BAD_REQUEST, "Evaluation gate failed: experiment is not selected")
        run = self._repository.get_latest_evaluation_run(int(experiment_id))
        if run is None:
            raise BizError(ErrorCode.BAD_REQUEST, "Evaluation gate failed: no completed run")
        pass_rate = float(run.get("pass_rate") or 0)
        status = str(run.get("status") or "")
        if status not in {"COMPLETED", "PASSED"} or pass_rate < float(gate["requiredPassRate"]):
            raise BizError(ErrorCode.BAD_REQUEST, "Evaluation gate failed: latest run did not pass")

    def _normalize_shell_config(self, config: Any) -> dict[str, Any]:
        return dict(config) if isinstance(config, dict) else {}
