from __future__ import annotations

from dataclasses import dataclass, field
from collections.abc import Mapping
import ast
import json
import re
import subprocess
from time import perf_counter
from typing import Any, Protocol

import httpx

from app.modules.chat.domain.tool_runner import McpToolExecutor
from app.modules.chat.domain.tool_schema import ToolDefinition
from app.modules.knowledge.api.facade import KnowledgeFacade
from app.modules.workflow.domain.context import ExecutionContext
from app.modules.workflow.infra.repository import WorkflowRepository

MAX_STEPS = 50
_LOCAL_TEMPLATE_PATTERN = re.compile(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}")


class WorkflowExecutionError(Exception):
    pass


class WorkflowInterrupt(Exception):
    def __init__(self, output: dict[str, Any]) -> None:
        super().__init__("Workflow interrupted")
        self.output = output


@dataclass(frozen=True)
class WorkflowExecutionResult:
    run_id: int
    status: str
    output: dict[str, Any]
    variable_scopes: dict[str, dict[str, Any]] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkflowNodeExecutionResult:
    node_key: str
    status: str
    input: dict[str, Any]
    output: dict[str, Any]
    elapsed_ms: int


@dataclass(frozen=True)
class ResourceExecutionPolicy:
    timeout_ms: int
    retry_count: int
    error_behavior: str
    allow_write: bool


@dataclass(frozen=True)
class AgentInvocationResult:
    session_id: int
    content: str
    status: str
    latency_ms: int
    tool_calls: list[dict[str, Any]]


class NodeExecutor(Protocol):
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        ...


class WorkflowLlmCompleter(Protocol):
    def complete_prompt(self, prompt: str, options: dict[str, Any] | None = None) -> str:
        ...

    def supports_tool_calls(self) -> bool:
        ...

    def complete_prompt_with_tools(
        self,
        prompt: str,
        options: dict[str, Any] | None,
        tools: list[ToolDefinition],
        tool_ids: list[int],
        mcp_facade: McpToolExecutor,
    ) -> tuple[str, list[dict[str, Any]]]:
        ...


class HandoffTicketCreator(Protocol):
    def create_ticket(self, data: dict[str, Any]) -> dict[str, Any]:
        ...


class AgentInvocationFacade(Protocol):
    def invoke_agent(
        self,
        *,
        agent_id: int,
        message: str,
        variables: dict[str, Any],
        history: list[dict[str, Any]],
        timeout_ms: int,
        parent_agent_ids: tuple[int, ...],
        max_depth: int,
    ) -> AgentInvocationResult:
        ...


class ApiToolExecutor(Protocol):
    def execute_api_tool(
        self,
        resource_id: str,
        tool_name: str,
        arguments: dict[str, object],
        timeout_ms: int | None = None,
    ) -> Any:
        ...

    def execute_api_resource(
        self,
        resource_id: str,
        arguments: dict[str, object],
        overrides: dict[str, Any] | None = None,
        timeout_ms: int | None = None,
    ) -> Any:
        ...


class StartNodeExecutor:
    def __init__(self, input_data: dict[str, Any]) -> None:
        self._input_data = input_data

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        return dict(self._input_data)


class LlmNodeExecutor:
    def __init__(
        self,
        completer: WorkflowLlmCompleter | None = None,
        knowledge_facade: KnowledgeFacade | None = None,
        mcp_tool_executor: McpToolExecutor | None = None,
    ) -> None:
        self._completer = completer
        self._knowledge_facade = knowledge_facade
        self._mcp_tool_executor = mcp_tool_executor

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "answer")
        local_inputs = _node_inputs(config, context)
        system_prompt, prompt = _render_llm_prompts(config, context, local_inputs)
        prompt = self._with_resource_context(config, context, prompt)
        llm_options = _llm_options(config)
        if system_prompt:
            llm_options["systemPrompt"] = system_prompt
        else:
            llm_options.pop("systemPrompt", None)
        tool_resources = _callable_tool_resources(config)
        if tool_resources and _tool_choice_mode(config) != "disabled":
            return self._execute_with_tools(node, config, prompt, output_variable, llm_options)
        if self._completer is not None:
            answer = self._completer.complete_prompt(prompt, llm_options)
            return self._output_with_stream_events(
                config,
                str(node["node_key"]),
                output_variable,
                answer,
                _debug_extra_from_completer(self._completer),
            )
        return self._output_with_stream_events(config, str(node["node_key"]), output_variable, f"LLM mock: {prompt}")

    def _execute_with_tools(
        self,
        node: dict[str, Any],
        config: dict[str, Any],
        prompt: str,
        output_variable: str,
        llm_options: dict[str, Any],
    ) -> dict[str, Any]:
        if self._completer is None:
            raise WorkflowExecutionError("LLM callable tools require a configured LLM provider")
        if self._mcp_tool_executor is None:
            raise WorkflowExecutionError("LLM callable tools require a tool runtime")
        if not self._completer.supports_tool_calls():
            raise WorkflowExecutionError("Selected Workflow LLM provider/model does not support tool calls")
        if not hasattr(self._mcp_tool_executor, "tool_definitions_for_servers"):
            raise WorkflowExecutionError("LLM callable tools require tool schema registry support")

        tool_resources = _callable_tool_resources(config)
        tool_ids = _callable_tool_server_ids(tool_resources)
        if not tool_ids:
            raise WorkflowExecutionError("LLM callable tools require at least one server id")
        tool_names = {str(resource.get("toolName") or "").strip() for resource in tool_resources if resource.get("toolName")}
        definitions = list(self._mcp_tool_executor.tool_definitions_for_servers(tool_ids))  # type: ignore[attr-defined]
        tools = [tool for tool in definitions if not tool_names or tool.name in tool_names]
        if not tools:
            raise WorkflowExecutionError("No callable tool schemas are available for LLM node")
        answer, tool_calls = self._completer.complete_prompt_with_tools(
            prompt=prompt,
            options=llm_options,
            tools=tools,
            tool_ids=tool_ids,
            mcp_facade=self._mcp_tool_executor,
        )
        return self._output_with_stream_events(
            config,
            str(node["node_key"]),
            output_variable,
            answer,
            {
                "toolCalls": tool_calls,
                "toolSettings": _llm_tool_settings(config),
                **_debug_extra_from_completer(self._completer),
            },
        )

    def _output_with_stream_events(
        self,
        config: dict[str, Any],
        node_key: str,
        output_variable: str,
        answer: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        values = {output_variable: answer, **(extra or {})}
        output = _declared_output_or_all(values, config)
        for key, value in (extra or {}).items():
            output.setdefault(key, value)
        output["events"] = _llm_stream_events(config, node_key, answer)
        usage = output.get("__usage")
        if isinstance(usage, Mapping):
            output["events"].append(_node_usage_event(node_key, usage))
        return output

    def _with_resource_context(self, config: dict[str, Any], context: ExecutionContext, prompt: str) -> str:
        snippets: list[str] = []
        for resource in _resource_items(config):
            resource_type = _resource_type(resource)
            if resource_type == "knowledge":
                snippets.extend(self._knowledge_context(resource, context, prompt))
                continue
            if resource_type == "mcp":
                continue
            if resource_type == "subworkflow":
                raise WorkflowExecutionError("Subworkflow resources are not runnable inside LLM nodes until nested-run runtime is wired")
            raise WorkflowExecutionError(f"Unsupported LLM resource type: {resource_type}")
        history = _history_context(config, context)
        if not snippets and not history:
            return prompt
        blocks: list[str] = []
        if snippets:
            context_block = "\n".join(f"- {snippet}" for snippet in snippets)
            blocks.append(f"Knowledge Context:\n{context_block}")
        if history:
            history_block = "\n".join(f"- {item}" for item in history)
            blocks.append(f"Conversation History:\n{history_block}")
        joined_blocks = "\n\n".join(blocks)
        return f"{joined_blocks}\n\nUser Prompt:\n{prompt}"

    def _knowledge_context(self, resource: dict[str, Any], context: ExecutionContext, prompt: str) -> list[str]:
        if self._knowledge_facade is None:
            raise WorkflowExecutionError("Workflow knowledge facade is not configured")
        knowledge_base_id = _resource_id(resource)
        if knowledge_base_id is None:
            raise WorkflowExecutionError("Knowledge resource requires knowledgeBaseId")
        query = context.render(str(resource.get("query") or prompt))
        top_k = _positive_int(resource.get("topK") or resource.get("top_k"), default=3)
        return [
            result.content
            for result in self._knowledge_facade.search_chunks(
                knowledge_base_id,
                query,
                top_k=top_k,
                retrieval_mode=_retrieval_mode(resource.get("retrievalMode") or resource.get("retrieval_mode")),
                score_threshold=_score_threshold(
                    resource.get("scoreThreshold") or resource.get("score_threshold")
                ),
                rerank=_bool_setting(resource.get("rerank"), default=False),
            )
        ]


class ApiCallNodeExecutor:
    def __init__(self, api_tool_executor: ApiToolExecutor | None = None) -> None:
        self._api_tool_executor = api_tool_executor

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "response")
        resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
        if resource_id:
            if self._api_tool_executor is None:
                raise WorkflowExecutionError("API Resource runtime is not configured")
            arguments = _mapped_arguments(config, context)
            result = self._api_tool_executor.execute_api_resource(
                resource_id,
                arguments,
                overrides={
                    "method": config.get("method"),
                    "endpoint": config.get("url") or config.get("endpoint"),
                    "headers": config.get("headers"),
                    "body": config.get("body"),
                    "bodyTemplate": config.get("bodyTemplate"),
                },
                timeout_ms=_positive_int(config.get("timeoutMs") or config.get("timeout") or 30_000, default=30_000),
            )
            if not result.success:
                raise WorkflowExecutionError(str(result.error_message or "API Resource call failed"))
            return {output_variable: result.response.get("body"), "evidence": result.evidence}
        method = str(config.get("method") or "GET").upper()
        url = context.render(str(config.get("url") or config.get("endpoint") or ""))
        timeout = _positive_float(config.get("timeout"), default=30.0)
        headers = _render_headers(config.get("headers"), context)
        body = _render_payload(config.get("body"), context)
        request_kwargs: dict[str, Any] = {"headers": headers}
        if body is not None:
            if isinstance(body, str):
                request_kwargs["content"] = body
            else:
                request_kwargs["json"] = body
        try:
            with httpx.Client(timeout=timeout, trust_env=False) as client:
                response = client.request(method, url, **request_kwargs)
        except httpx.HTTPError as exc:
            raise WorkflowExecutionError(f"API call failed: {exc}") from exc
        if response.status_code >= 400:
            raise WorkflowExecutionError(f"API call failed: HTTP {response.status_code} {response.text}")
        return {output_variable: _response_payload(response)}


class ToolCallNodeExecutor:
    def __init__(
        self,
        mcp_tool_executor: McpToolExecutor | None = None,
        api_tool_executor: ApiToolExecutor | None = None,
    ) -> None:
        self._mcp_tool_executor = mcp_tool_executor
        self._api_tool_executor = api_tool_executor

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        resource_type = _normalized_resource_type(config.get("resourceType") or config.get("type") or "MCP_TOOL")
        if resource_type in {"API_TOOL", "API_RESOURCE"}:
            return self._execute_api_tool(config, context, resource_type)
        if resource_type != "MCP_TOOL":
            raise WorkflowExecutionError(f"Unsupported TOOL_CALL resource type: {resource_type}")
        if self._mcp_tool_executor is None:
            raise WorkflowExecutionError("TOOL_CALL runtime is not configured")

        tool_name = str(config.get("toolName") or config.get("name") or "").strip()
        if not tool_name:
            raise WorkflowExecutionError("TOOL_CALL requires toolName")
        server_ids = _tool_server_ids(config)
        if not server_ids:
            raise WorkflowExecutionError("TOOL_CALL requires at least one server id")
        policy = _resource_execution_policy(config, tool_name)
        if _write_capable_tool(tool_name) and not policy.allow_write:
            raise WorkflowExecutionError(f"TOOL_CALL write-capable tool requires explicit allowWrite policy: {tool_name}")

        arguments = _tool_call_arguments(config, context)
        result = None
        error_message = ""
        elapsed_ms = 0
        attempts = 0
        for attempt_index in range(policy.retry_count + 1):
            attempts = attempt_index + 1
            started_at = perf_counter()
            result = self._mcp_tool_executor.execute_tool_call(server_ids, tool_name, arguments)
            elapsed_ms = result.elapsed_ms or int((perf_counter() - started_at) * 1000)
            error_message = _tool_result_error(result, elapsed_ms, policy.timeout_ms, tool_name)
            if not error_message:
                break
            if attempt_index >= policy.retry_count:
                break
        assert result is not None
        success = not error_message
        evidence = {
            "resourceId": str(config.get("resourceId") or ""),
            "resourceType": resource_type,
            "toolName": tool_name,
            "adapter": "mcp",
            "sanitizedInput": arguments,
            "latencyMs": elapsed_ms,
            "timeoutMs": policy.timeout_ms,
            "status": "SUCCEEDED" if success else "FAILED",
            "errorMessage": error_message,
            "retryCount": policy.retry_count,
            "attempts": attempts,
        }
        if not success:
            output = {
                "result": "",
                "success": False,
                "error": error_message,
                "evidence": evidence,
                "route": "error",
            }
            if policy.error_behavior in {"continue", "branch"}:
                return _declared_output(output, config)
            raise WorkflowExecutionError(error_message)

        output = {
            "result": result.result or "",
            "success": True,
            "error": "",
            "evidence": evidence,
            "route": "success",
        }
        return _declared_output(output, config)

    def _execute_api_tool(self, config: dict[str, Any], context: ExecutionContext, resource_type: str) -> dict[str, Any]:
        if self._api_tool_executor is None:
            raise WorkflowExecutionError("API-backed TOOL_CALL runtime is not configured")
        tool_name = str(config.get("toolName") or config.get("name") or "").strip()
        if not tool_name:
            raise WorkflowExecutionError("TOOL_CALL requires toolName")
        resource_id = str(config.get("resourceId") or config.get("resource_id") or "").strip()
        if not resource_id:
            raise WorkflowExecutionError("API-backed TOOL_CALL requires resourceId")
        policy = _resource_execution_policy(config, tool_name)
        arguments = _tool_call_arguments(config, context)
        result = None
        error_message = ""
        attempts = 0
        for attempt_index in range(policy.retry_count + 1):
            attempts = attempt_index + 1
            result = self._api_tool_executor.execute_api_tool(resource_id, tool_name, arguments, timeout_ms=policy.timeout_ms)
            error_message = "" if result.success else str(result.error_message or f"Tool call failed: {tool_name}")
            if not error_message:
                break
            if attempt_index >= policy.retry_count:
                break
        assert result is not None
        success = not error_message
        evidence = {
            **dict(result.evidence or {}),
            "resourceId": str(result.evidence.get("resourceId") or resource_id),
            "resourceType": "API_TOOL" if resource_type == "API_RESOURCE" else resource_type,
            "toolName": tool_name,
            "adapter": "API_RESOURCE",
            "sanitizedInput": arguments,
            "latencyMs": int(result.elapsed_ms or 0),
            "timeoutMs": policy.timeout_ms,
            "status": "SUCCEEDED" if success else "FAILED",
            "errorMessage": error_message,
            "retryCount": policy.retry_count,
            "attempts": attempts,
        }
        if not success:
            output = {
                "result": "",
                "success": False,
                "error": error_message,
                "evidence": evidence,
                "route": "error",
            }
            if policy.error_behavior in {"continue", "branch"}:
                return _declared_output(output, config)
            raise WorkflowExecutionError(error_message)
        output = {
            "result": result.result or "",
            "success": True,
            "error": "",
            "evidence": evidence,
            "route": "success",
        }
        return _declared_output(output, config)


class ExecuteWorkflowNodeExecutor:
    def __init__(
        self,
        repository: WorkflowRepository,
        current_workflow_id: int,
        parent_workflow_ids: tuple[int, ...],
        knowledge_facade: KnowledgeFacade | None = None,
        llm_completer: WorkflowLlmCompleter | None = None,
        mcp_tool_executor: McpToolExecutor | None = None,
        api_tool_executor: ApiToolExecutor | None = None,
        agent_invoker: AgentInvocationFacade | None = None,
        parent_agent_ids: tuple[int, ...] = (),
    ) -> None:
        self._repository = repository
        self._current_workflow_id = current_workflow_id
        self._parent_workflow_ids = parent_workflow_ids
        self._knowledge_facade = knowledge_facade
        self._llm_completer = llm_completer
        self._mcp_tool_executor = mcp_tool_executor
        self._api_tool_executor = api_tool_executor
        self._agent_invoker = agent_invoker
        self._parent_agent_ids = parent_agent_ids

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        target_workflow_id = _target_workflow_id(config)
        if target_workflow_id is None:
            raise WorkflowExecutionError("EXECUTE_WORKFLOW requires targetWorkflowId")
        if target_workflow_id == self._current_workflow_id or target_workflow_id in self._parent_workflow_ids:
            raise WorkflowExecutionError("EXECUTE_WORKFLOW recursive target is not allowed")

        max_depth = _execute_workflow_max_depth(config.get("maxDepth") if "maxDepth" in config else config.get("max_depth"))
        next_depth = len(self._parent_workflow_ids) + 1
        if next_depth > max_depth:
            raise WorkflowExecutionError("EXECUTE_WORKFLOW maxDepth exceeded")

        target = self._repository.get(target_workflow_id)
        if target is None:
            raise WorkflowExecutionError("EXECUTE_WORKFLOW target workflow not found")
        if str(target.get("flow_type") or "WORKFLOW") != "WORKFLOW":
            raise WorkflowExecutionError("EXECUTE_WORKFLOW target must be a Workflow")
        if str(target.get("status") or "") != "PUBLISHED":
            raise WorkflowExecutionError("EXECUTE_WORKFLOW target workflow must be published")

        nested_input = _mapped_arguments(config, context)
        nested_started_at = perf_counter()
        nested_result = WorkflowExecutionEngine(
            self._repository,
            knowledge_facade=self._knowledge_facade,
            llm_completer=self._llm_completer,
            mcp_tool_executor=self._mcp_tool_executor,
            agent_invoker=self._agent_invoker,
            parent_workflow_ids=(*self._parent_workflow_ids, self._current_workflow_id),
            parent_agent_ids=self._parent_agent_ids,
        ).run(target_workflow_id, nested_input)
        nested_latency_ms = int((perf_counter() - nested_started_at) * 1000)
        if nested_result.status == "INTERRUPTED":
            raise WorkflowExecutionError("EXECUTE_WORKFLOW nested interrupt is not supported")
        if nested_result.status != "SUCCEEDED":
            raise WorkflowExecutionError(f"EXECUTE_WORKFLOW nested run {nested_result.status.lower()}")

        output = _mapped_output(config, nested_result.output)
        mapped_output = dict(output)
        output.update(
            {
                "nestedRunId": nested_result.run_id,
                "status": nested_result.status,
                "latencyMs": nested_latency_ms,
                "mappedInputSummary": dict(nested_input),
                "mappedOutputSummary": mapped_output,
                "error": "",
            }
        )
        return _declared_output_or_all(output, config)


class AgentCallNodeExecutor:
    def __init__(
        self,
        agent_invoker: AgentInvocationFacade | None = None,
        parent_agent_ids: tuple[int, ...] = (),
    ) -> None:
        self._agent_invoker = agent_invoker
        self._parent_agent_ids = parent_agent_ids

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        if self._agent_invoker is None:
            raise WorkflowExecutionError("AGENT_CALL runtime is not configured")
        target_agent_id = _target_agent_id(config)
        if target_agent_id is None:
            raise WorkflowExecutionError("AGENT_CALL requires targetAgentId")

        mapped_input = _mapped_arguments(config, context)
        message = _agent_call_message(config, mapped_input, context)
        history = _agent_call_history(config, context)
        if history and str(config.get("historyMode") or "none").lower() in {"include", "all", "recent"}:
            message = f"{message}\n\nConversation history:\n{_format_agent_history(history)}"
        started_at = perf_counter()
        timeout_raw = config.get("timeoutMs") if "timeoutMs" in config else config.get("timeout_ms")
        timeout_ms = _agent_call_timeout_ms(timeout_raw)
        result = self._agent_invoker.invoke_agent(
            agent_id=target_agent_id,
            message=message,
            variables={key: value for key, value in mapped_input.items() if key != "message"},
            history=history,
            timeout_ms=timeout_ms,
            parent_agent_ids=self._parent_agent_ids,
            max_depth=_execute_workflow_max_depth(config.get("maxDepth") if "maxDepth" in config else config.get("max_depth")),
        )
        latency_ms = result.latency_ms or int((perf_counter() - started_at) * 1000)
        if latency_ms > timeout_ms:
            raise WorkflowExecutionError("AGENT_CALL timed out")
        raw_output = {
            "answer": result.content,
            "sessionId": result.session_id,
            "status": result.status,
            "latencyMs": latency_ms,
            "toolCalls": result.tool_calls,
            "error": "",
        }
        output = _mapped_output(config, raw_output)
        mapped_output = dict(output)
        output.update(
            {
                "sessionId": result.session_id,
                "status": result.status,
                "latencyMs": latency_ms,
                "mappedInputSummary": dict(mapped_input),
                "mappedOutputSummary": mapped_output,
                "toolCalls": result.tool_calls,
                "error": "",
            }
        )
        declared_output = _declared_output_or_all(output, config)
        declared_output["events"] = _agent_stream_events(config, str(node["node_key"]), str(result.content or ""))
        return declared_output


class CodeNodeExecutor:
    _safe_builtins = {
        "abs": abs,
        "all": all,
        "any": any,
        "bool": bool,
        "dict": dict,
        "float": float,
        "int": int,
        "len": len,
        "list": list,
        "max": max,
        "min": min,
        "round": round,
        "sorted": sorted,
        "str": str,
        "sum": sum,
        "tuple": tuple,
    }
    _blocked_call_names = {"__import__", "open", "eval", "exec", "compile", "input", "globals", "locals", "vars"}
    _blocked_nodes = (ast.Import, ast.ImportFrom, ast.Global, ast.Nonlocal)

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        language = str(config.get("language") or "python").lower()
        code = str(config.get("code") or config.get("body") or "").strip()
        if not code:
            raise WorkflowExecutionError("CODE node requires code")
        inputs = _node_inputs(config, context)
        if language in {"javascript", "js"}:
            return self._execute_javascript(code, inputs, config)
        if language not in {"python", "python3"}:
            raise WorkflowExecutionError(f"Unsupported CODE language: {language}")
        tree = _validated_code_tree(code)
        local_vars: dict[str, Any] = {
            "args": inputs,
            "inputs": inputs,
            "params": inputs,
            "result": None,
        }
        sandbox_globals = {
            "__builtins__": self._safe_builtins,
            "args": inputs,
            "inputs": inputs,
            "json": json,
            "params": inputs,
            "re": re,
        }
        exec(  # noqa: S102 - deliberate restricted workflow node sandbox.
            compile(tree, "<workflow-code-node>", "exec"),
            sandbox_globals,
            local_vars,
        )
        main_function = local_vars.get("main") or sandbox_globals.get("main")
        if callable(main_function):
            result = main_function(inputs)
        else:
            result = local_vars.get("result")
        if result is None:
            result = local_vars.get("output")
        if not isinstance(result, Mapping):
            output_variable = str(config.get("outputVariable") or "output")
            return {output_variable: result}
        return _declared_output(dict(result), config)

    def _execute_javascript(self, code: str, inputs: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
        timeout_seconds = _code_timeout_seconds(config)
        runner = """
const fs = require('node:fs');
const vm = require('node:vm');

(async () => {
  const payload = JSON.parse(fs.readFileSync(0, 'utf8'));
  const module = { exports: {} };
  const args = Object.assign({}, payload.inputs, { params: payload.inputs, inputs: payload.inputs });
  const sandbox = {
    args,
    params: payload.inputs,
    inputs: payload.inputs,
    result: undefined,
    output: undefined,
    module,
    exports: module.exports,
    console: { log() {}, warn() {}, error() {} },
    URL,
    URLSearchParams,
    TextEncoder,
    TextDecoder,
    structuredClone,
    atob,
    btoa,
  };
  sandbox.globalThis = sandbox;
  vm.createContext(sandbox);
  const source = `${payload.code}
;(async () => {
  const exportedMain = typeof module.exports === 'function' ? module.exports : module.exports && module.exports.main;
  if (typeof exportedMain === 'function') return await exportedMain(args);
  if (typeof exports.main === 'function') return await exports.main(args);
  if (typeof main === 'function') return await main(args);
  if (typeof result !== 'undefined') return result;
  if (typeof output !== 'undefined') return output;
  return undefined;
})()`;
  const script = new vm.Script(source, { filename: 'workflow-code-node.js' });
  const value = await script.runInContext(sandbox, { timeout: payload.timeoutMs });
  process.stdout.write(JSON.stringify({ ok: true, value }));
})().catch((error) => {
  process.stdout.write(JSON.stringify({ ok: false, error: String(error && error.message ? error.message : error) }));
  process.exitCode = 1;
});
"""
        payload = {"code": code, "inputs": inputs, "timeoutMs": int(timeout_seconds * 1000)}
        try:
            completed = subprocess.run(  # noqa: S603 - fixed executable and no shell.
                ["node", "-e", runner],
                input=json.dumps(payload),
                capture_output=True,
                text=True,
                timeout=timeout_seconds + 1,
                check=False,
            )
        except FileNotFoundError as exc:
            raise WorkflowExecutionError("CODE JavaScript runtime is not available") from exc
        except subprocess.TimeoutExpired as exc:
            raise WorkflowExecutionError("CODE node timed out") from exc
        try:
            response = json.loads(completed.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise WorkflowExecutionError("CODE JavaScript runtime returned invalid output") from exc
        if completed.returncode != 0 or response.get("ok") is not True:
            message = response.get("error") or completed.stderr.strip() or "CODE JavaScript execution failed"
            raise WorkflowExecutionError(str(message))
        result = response.get("value")
        if not isinstance(result, Mapping):
            output_variable = str(config.get("outputVariable") or "output")
            return {output_variable: result}
        return _declared_output(dict(result), config)


class TextProcessNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        operation = str(config.get("operation") or "format_template").lower()
        output_variable = _first_output_name(config, "text")
        if operation in {"format_template", "template", "format"}:
            value = context.render(str(config.get("template") or config.get("source") or ""))
            return {output_variable: value}
        if operation in {"concatenate", "concat"}:
            parts = config.get("parts") or config.get("texts") or []
            if not isinstance(parts, list):
                parts = [parts]
            separator = context.render(str(config.get("separator") or ""))
            value = separator.join(context.render(str(part)) for part in parts)
            return {output_variable: value}
        if operation in {"extract_regex", "regex_extract", "extract"}:
            source = context.render(str(config.get("source") or config.get("text") or ""))
            pattern = str(config.get("pattern") or "")
            if not pattern:
                raise WorkflowExecutionError("TEXT_PROCESS regex extraction requires pattern")
            match = re.search(pattern, source)
            group = config.get("group", 0)
            try:
                extracted = match.group(group) if match else ""
            except IndexError as exc:
                raise WorkflowExecutionError(f"TEXT_PROCESS regex group not found: {group}") from exc
            return {
                output_variable: extracted,
                "matched": match is not None,
                "groups": list(match.groups()) if match else [],
            }
        if operation == "replace":
            source = context.render(str(config.get("source") or config.get("text") or ""))
            pattern = str(config.get("pattern") or config.get("search") or "")
            replacement = context.render(str(config.get("replacement") or ""))
            return {output_variable: re.sub(pattern, replacement, source) if pattern else source}
        if operation == "trim":
            source = context.render(str(config.get("source") or config.get("text") or ""))
            return {output_variable: source.strip()}
        raise WorkflowExecutionError(f"Unsupported TEXT_PROCESS operation: {operation}")


class JsonParseNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = _first_output_name(config, str(config.get("outputVariable") or "parsed"))
        source = _source_value(config, context)
        if isinstance(source, str):
            try:
                parsed = json.loads(source)
            except json.JSONDecodeError as exc:
                return {
                    output_variable: None,
                    "parsed": None,
                    "parseStatus": "FAILED",
                    "errorMessage": exc.msg,
                }
        else:
            parsed = source
        output = {
            output_variable: parsed,
            "parsed": parsed,
            "parseStatus": "SUCCEEDED",
            "errorMessage": "",
        }
        for item in _field_map(config):
            name = str(item.get("name") or "").strip()
            if not name:
                continue
            output[name] = _json_path_value(parsed, str(item.get("path") or item.get("source") or ""))
        return output


class VariableAggregationNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        groups = _aggregation_groups(config, context)
        if groups:
            output: dict[str, Any] = {}
            source_status: list[dict[str, Any]] = []
            for group in groups:
                name = group["name"]
                variables = group["variables"]
                output[name] = next((item["value"] for item in variables if _not_empty(item["value"])), None)
                source_status.append(
                    {
                        "name": name,
                        "empty": not _not_empty(output[name]),
                        "variables": [
                            {"empty": not _not_empty(item["value"])}
                            for item in variables
                        ],
                    },
                )
            output["sourceStatus"] = source_status
            return output

        output_variable = _first_output_name(config, str(config.get("outputVariable") or "aggregate"))
        sources = _aggregation_sources(config, context)
        strategy = str(config.get("strategy") or config.get("mergeStrategy") or "first_non_empty").lower()
        default_value = _render_optional(config.get("defaultValue"), context)
        value: Any
        if strategy in {"first_non_empty", "first", "coalesce"}:
            value = next((source["value"] for source in sources if _not_empty(source["value"])), default_value)
        elif strategy in {"last_non_empty", "last"}:
            value = next((source["value"] for source in reversed(sources) if _not_empty(source["value"])), default_value)
        elif strategy in {"concat", "concatenate"}:
            separator = context.render(str(config.get("separator") or ""))
            value = separator.join(str(source["value"]) for source in sources if _not_empty(source["value"]))
            if value == "" and default_value is not None:
                value = default_value
        elif strategy in {"array", "list"}:
            value = [source["value"] for source in sources if _not_empty(source["value"])]
            if not value and default_value is not None:
                value = default_value
        elif strategy in {"object_merge", "merge_object"}:
            merged: dict[str, Any] = {}
            for source in sources:
                if isinstance(source["value"], Mapping):
                    merged.update(source["value"])
                elif source["name"] and _not_empty(source["value"]):
                    merged[str(source["name"])] = source["value"]
            value = merged or default_value
        else:
            raise WorkflowExecutionError(f"Unsupported VARIABLE_AGGREGATION strategy: {strategy}")
        return {
            output_variable: value,
            "sourceStatus": [
                {"name": source["name"], "empty": not _not_empty(source["value"])}
                for source in sources
            ],
        }


class VariableAssignNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        scope = str(config.get("targetScope") or config.get("scope") or "flow").strip().lower()
        variable_name = str(config.get("targetVariable") or config.get("variable") or "").strip()
        if not variable_name:
            raise WorkflowExecutionError("VARIABLE_ASSIGN requires targetVariable")
        write_mode = str(config.get("writeMode") or "set").strip().lower()
        if write_mode not in {"set", "append", "clear"}:
            raise WorkflowExecutionError(f"Unsupported VARIABLE_ASSIGN writeMode: {write_mode}")
        value = _assignment_source_value(config, context, scope, variable_name)
        try:
            written_value = context.set_scope_value(scope, variable_name, value, write_mode)
        except ValueError as exc:
            raise WorkflowExecutionError(str(exc)) from exc
        output_variable = _first_output_name(config, str(config.get("outputVariable") or "assigned"))
        return {
            output_variable: written_value,
            "assigned": write_mode != "clear",
            "scope": scope,
            "variable": variable_name,
            "value": written_value,
        }


class IntentRecognitionNodeExecutor:
    def __init__(self, completer: WorkflowLlmCompleter | None = None) -> None:
        self._completer = completer

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "intent")
        text = context.render(str(config.get("inputSource") or config.get("input") or "{{start.sys.query}}"))
        history = _history_context(config, context)
        if history:
            text = f"{' '.join(history)} {text}"
        intents = _intent_items(config)
        if not intents:
            raise WorkflowExecutionError("INTENT_RECOGNITION requires intents")
        mode = str(config.get("classifierMode") or "fake").lower()
        if mode == "llm" and self._completer is not None:
            picked = self._classify_with_llm(text, intents, config)
        else:
            picked = _classify_intent_fake(text, intents, str(config.get("defaultIntent") or "default"))
        output = {
            output_variable: picked["intent"],
            "intent": picked["intent"],
            "confidence": picked["confidence"],
            "reason": picked["reason"],
        }
        if self._completer is not None:
            output.update(_debug_extra_from_completer(self._completer))
        usage = output.get("__usage")
        if isinstance(usage, Mapping):
            output["events"] = [_node_usage_event(str(node["node_key"]), usage)]
        return output

    def _classify_with_llm(
        self,
        text: str,
        intents: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        assert self._completer is not None
        keys = [str(item["key"]) for item in intents]
        prompt = (
            "Classify the user intent. Return only one key from this list: "
            f"{', '.join(keys)}.\n"
            "Intents:\n"
            + "\n".join(
                f"- {item['key']}: {item.get('name', '')}; {item.get('description', '')}; examples={item.get('examples', [])}"
                for item in intents
            )
            + f"\nUser text: {text}"
        )
        raw = self._completer.complete_prompt(prompt, _llm_options(config)).strip()
        matched_key = next((key for key in keys if key.lower() in raw.lower()), None)
        if matched_key is None:
            return _classify_intent_fake(text, intents, str(config.get("defaultIntent") or "default"))
        return {"intent": matched_key, "confidence": 0.9, "reason": "matched by llm classifier"}


class MessageNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "content")
        content = context.render(str(config.get("content") or config.get("message") or ""))
        stream_output = str(config.get("streamOutput") or "inherit").lower()
        stream_target = str(config.get("streamTarget") or "message").strip() or "message"
        fallback_mode = str(config.get("fallbackMode") or "aggregate").strip() or "aggregate"
        events: list[dict[str, Any]] = []
        if stream_output in {"enabled", "true", "1", "inherit"}:
            events.append({
                "type": "message_delta",
                "nodeKey": node["node_key"],
                "content": content,
                "target": stream_target,
                "fallbackMode": fallback_mode,
            })
        events.append({
            "type": "message_done",
            "nodeKey": node["node_key"],
            "content": content,
            "target": stream_target,
            "fallbackMode": fallback_mode,
        })
        return {
            output_variable: content,
            "content": content,
            "events": events,
        }


class QuestionNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        node_key = str(node["node_key"])
        output_variable = str(config.get("outputVariable") or "answer")
        resume = _resume_payload(context, node_key)
        if resume is not None:
            answer = resume.get("answer") if isinstance(resume, Mapping) else resume
            return {
                output_variable: answer,
                "answer": answer,
                "normalizedAnswer": str(answer).strip() if answer is not None else "",
                "validationStatus": "VALID",
            }
        question = context.render(str(config.get("question") or config.get("content") or ""))
        output = {
            "interrupt": {
                "type": "QUESTION",
                "nodeKey": node_key,
                "question": question,
                "answerType": str(config.get("answerType") or "text"),
                "options": config.get("options") if isinstance(config.get("options"), list) else [],
                "resumeBehavior": str(config.get("resumeBehavior") or "wait"),
                "timeoutSeconds": _non_negative_int(config.get("timeoutSeconds") or config.get("timeout_seconds"), default=0),
            },
            "events": [
                {"type": "message_done", "nodeKey": node_key, "content": question},
                {"type": "interrupt", "nodeKey": node_key, "interruptType": "QUESTION"},
            ],
        }
        raise WorkflowInterrupt(output)


class HumanInputNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        node_key = str(node["node_key"])
        output_variable = str(config.get("outputVariable") or "payload")
        resume = _resume_payload(context, node_key)
        if resume is not None:
            payload = resume.get("payload") if isinstance(resume, Mapping) and "payload" in resume else resume
            if isinstance(payload, Mapping):
                output = dict(payload)
                output[output_variable] = dict(payload)
                return output
            return {output_variable: payload}
        prompt = context.render(str(config.get("prompt") or ""))
        output = {
            "interrupt": {
                "type": "HUMAN_INPUT",
                "nodeKey": node_key,
                "prompt": prompt,
                "approvalMode": str(config.get("approvalMode") or "input"),
                "assigneeRole": str(config.get("assigneeRole") or ""),
                "inputSchema": config.get("inputSchema") if isinstance(config.get("inputSchema"), list) else [],
            },
            "events": [
                {"type": "interrupt", "nodeKey": node_key, "interruptType": "HUMAN_INPUT"},
            ],
        }
        raise WorkflowInterrupt(output)


class TransferToHumanNodeExecutor:
    def __init__(
        self,
        flow_type: str,
        handoff_service: HandoffTicketCreator | None,
    ) -> None:
        self._flow_type = flow_type
        self._handoff_service = handoff_service

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        if self._flow_type != "CHATFLOW":
            raise WorkflowExecutionError("TRANSFER_TO_HUMAN is Chatflow-only")
        if self._handoff_service is None:
            raise WorkflowExecutionError("TRANSFER_TO_HUMAN handoff service is not configured")
        config = _config(node)
        start_values = context.get_output("start")
        session_id = str(
            start_values.get("sys.conversation_id")
            or start_values.get("conversationId")
            or start_values.get("sessionId")
            or ""
        )
        if not session_id:
            session_id = f"handoff-{node['node_key']}"
        queue = str(config.get("queue") or config.get("team") or "general")
        reason = str(config.get("reason") or config.get("category") or "user_request")
        priority = str(config.get("priority") or "normal")
        message = context.render(str(config.get("message") or "已为你转接人工客服，请稍候。"))
        ticket = self._handoff_service.create_ticket(
            {
                "session_id": session_id,
                "conversation_id": str(start_values.get("sys.conversation_id") or start_values.get("conversationId") or session_id),
                "user_id": str(start_values.get("sys.user_id") or start_values.get("userId") or ""),
                "channel": str(start_values.get("sys.channel") or start_values.get("channel") or "web"),
                "queue": queue,
                "reason": reason,
                "priority": priority,
                "sla_minutes": config.get("slaMinutes") or config.get("sla_minutes") or 30,
                "transcript_snapshot": _handoff_transcript(start_values),
                "context_snapshot": {
                    "nodeKey": node["node_key"],
                    "variables": context.scopes_snapshot(),
                    "nodeOutputs": {
                        "start": start_values,
                    },
                },
            }
        )
        output = {
            "handoff_id": ticket["id"],
            "handoff_status": ticket["status"],
            "queue": ticket["queue"],
            "assignee": ticket["assignee"],
            "reason": ticket["reason"],
            "priority": ticket["priority"],
            "events": [
                {"type": "message_done", "nodeKey": node["node_key"], "content": message},
                {
                    "type": "handoff_requested",
                    "nodeKey": node["node_key"],
                    "handoffId": ticket["id"],
                    "queue": ticket["queue"],
                    "priority": ticket["priority"],
                    "reason": ticket["reason"],
                },
            ],
            "interrupt": {
                "type": "TRANSFER_TO_HUMAN",
                "nodeKey": node["node_key"],
                "handoffId": ticket["id"],
                "queue": ticket["queue"],
                "status": ticket["status"],
                "message": message,
            },
        }
        raise WorkflowInterrupt(output)


class InformationCollectionNodeExecutor:
    def __init__(self, completer: WorkflowLlmCompleter | None = None) -> None:
        self._completer = completer

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        node_key = str(node["node_key"])
        fields = _collection_fields(config)
        if not fields:
            raise WorkflowExecutionError("INFORMATION_COLLECTION requires fields")
        output_variable = str(config.get("outputVariable") or config.get("collectionKey") or "collected")
        previous = _collection_previous_state(config, context, node_key)
        current_turn_fields = [field for field in fields if _collection_field_current_turn_only(field)]
        history_enabled_fields = [field for field in fields if not _collection_field_current_turn_only(field)]
        extracted: dict[str, Any] = {}
        if history_enabled_fields:
            extracted.update(self._extract(_collection_input_text(config, context, node_key), history_enabled_fields, config))
        if current_turn_fields:
            extracted.update(self._extract(_collection_current_turn_text(config, context, node_key), current_turn_fields, config))
        debug_extra = _debug_extra_from_completer(self._completer)
        raw_collected = {**previous, **extracted}
        collected = {key: value for key, value in raw_collected.items() if _collection_value_present(value)}
        missing = [
            str(field["name"])
            for field in fields
            if field.get("required") is True and not _collection_value_present(collected.get(str(field["name"])))
        ]
        output = {
            output_variable: collected,
            "collected": collected,
            **collected,
            "missing": missing,
            "complete": len(missing) == 0,
            "followup": "",
            "errors": [],
            **debug_extra,
        }
        if not missing:
            _write_collection_targets(fields, collected, context)
            if _bool_setting(config.get("writeToConversation"), default=False):
                for key, value in collected.items():
                    context.set_scope_value("conversation", str(key), value, "set")
            usage = output.get("__usage")
            if isinstance(usage, Mapping):
                output["events"] = [_node_usage_event(node_key, usage)]
            return output

        max_rounds = _positive_int(config.get("maxRounds") or config.get("max_rounds"), default=3)
        current_round = _collection_round(context, node_key)
        if current_round >= max_rounds:
            output["errors"] = ["max rounds reached"]
            return output

        followup = _collection_followup(config, missing, fields, collected)
        events: list[dict[str, Any]] = []
        stream_output = str(config.get("streamOutput") or "inherit").lower()
        if stream_output in {"enabled", "true", "1", "inherit"}:
            events.append({"type": "message_delta", "nodeKey": node_key, "content": followup})
        usage = output.get("__usage")
        if isinstance(usage, Mapping):
            events.append(_node_usage_event(node_key, usage))
        events.extend(
            [
                {"type": "message_done", "nodeKey": node_key, "content": followup},
                {"type": "interrupt", "nodeKey": node_key, "interruptType": "INFORMATION_COLLECTION"},
            ]
        )
        output.update(
            {
                "followup": followup,
                "events": events,
                "interrupt": {
                    "type": "INFORMATION_COLLECTION",
                    "nodeKey": node_key,
                    "collectionKey": str(config.get("collectionKey") or output_variable),
                    "collected": collected,
                    "missing": missing,
                    "followup": followup,
                    "round": current_round + 1,
                },
            }
        )
        raise WorkflowInterrupt(output)

    def _extract(
        self,
        text: str,
        fields: list[dict[str, Any]],
        config: dict[str, Any],
    ) -> dict[str, Any]:
        mode = str(config.get("extractorMode") or "fake").lower()
        if mode == "llm" and self._completer is not None:
            try:
                return _extract_collection_values_llm(self._completer, text, fields, config)
            except Exception:
                return _extract_collection_values_fake(text, fields)
        return _extract_collection_values_fake(text, fields)


class KnowledgeNodeExecutor:
    def __init__(self, knowledge_facade: KnowledgeFacade | None = None) -> None:
        self._knowledge_facade = knowledge_facade

    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "answer")
        query = context.render(str(config.get("query") or ""))
        knowledge_base_id = config.get("knowledgeBaseId") or config.get("knowledge_base_id")
        if self._knowledge_facade is None or knowledge_base_id is None:
            return {output_variable: f"Knowledge mock: {query}"}
        top_k = _positive_int(config.get("topK") or config.get("top_k"), default=1)
        results = self._knowledge_facade.search_chunks(
            int(knowledge_base_id),
            query,
            top_k=top_k,
            retrieval_mode=_retrieval_mode(config.get("retrievalMode") or config.get("retrieval_mode")),
            score_threshold=_score_threshold(config.get("scoreThreshold") or config.get("score_threshold")),
            rerank=_bool_setting(config.get("rerank"), default=False),
        )
        content = results[0].content if results else ""
        return {output_variable: content}


class ConditionNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        output_variable = str(config.get("outputVariable") or "route")
        branch = _matched_condition_branch(config, context)
        if branch is not None:
            return {output_variable: branch}
        expression = context.render(str(config.get("expression") or ""))
        return {output_variable: expression}


class EndNodeExecutor:
    def execute(self, node: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
        config = _config(node)
        declared_output = _declared_end_output(config, context)
        has_declared_output = isinstance(config.get("outputParameters"), list)
        return_mode = str(config.get("returnMode") or "").lower()
        variable_return_mode = return_mode in {"variables", "返回变量"}
        output_variable = str(config.get("outputVariable") or next(iter(declared_output), "output") or "output")
        if "output" in config and not variable_return_mode:
            rendered_output = _render_local_template(context.render(str(config["output"])), declared_output)
            return {output_variable: rendered_output}
        if declared_output or has_declared_output:
            return declared_output
        return {output_variable: context.find_value(output_variable)}


class ConditionBranchPicker:
    def pick(self, node_key: str, edges: list[dict[str, Any]], branch_value: str) -> str | None:
        source_edges = [edge for edge in edges if edge["source_node_key"] == node_key]
        matched = next(
            (
                edge
                for edge in source_edges
                if edge.get("condition_expr") is not None and str(edge["condition_expr"]) == branch_value
            ),
            None,
        )
        if matched:
            return str(matched["target_node_key"])
        default = next((edge for edge in source_edges if not edge.get("condition_expr")), None)
        return str(default["target_node_key"]) if default else None


class WorkflowExecutionEngine:
    def __init__(
        self,
        repository: WorkflowRepository,
        knowledge_facade: KnowledgeFacade | None = None,
        llm_completer: WorkflowLlmCompleter | None = None,
        mcp_tool_executor: McpToolExecutor | None = None,
        api_tool_executor: ApiToolExecutor | None = None,
        agent_invoker: AgentInvocationFacade | None = None,
        parent_workflow_ids: tuple[int, ...] = (),
        parent_agent_ids: tuple[int, ...] = (),
        flow_type: str = "WORKFLOW",
        handoff_service: HandoffTicketCreator | None = None,
    ) -> None:
        self._repository = repository
        self._knowledge_facade = knowledge_facade
        self._llm_completer = llm_completer
        self._mcp_tool_executor = mcp_tool_executor
        self._api_tool_executor = api_tool_executor
        self._agent_invoker = agent_invoker
        self._parent_workflow_ids = parent_workflow_ids
        self._parent_agent_ids = parent_agent_ids
        self._flow_type = flow_type
        self._handoff_service = handoff_service
        self._last_variable_scopes: dict[str, dict[str, Any]] = {}

    def run(self, workflow_id: int, input_data: dict[str, Any]) -> WorkflowExecutionResult:
        workflow = self._repository.get(workflow_id)
        if workflow is None:
            raise WorkflowExecutionError("Workflow not found")
        nodes = self._repository.list_nodes(workflow_id)
        edges = self._repository.list_edges(workflow_id)
        run_id = self._repository.create_run(workflow_id, input_data)
        self._last_variable_scopes = {}
        try:
            output = self._run_graph(workflow_id, run_id, nodes, edges, input_data)
            self._repository.finish_run(run_id, "SUCCEEDED", output=output)
            return WorkflowExecutionResult(
                run_id=run_id,
                status="SUCCEEDED",
                output=output,
                variable_scopes=self._last_variable_scopes,
            )
        except WorkflowInterrupt as exc:
            self._repository.finish_run(run_id, "INTERRUPTED", output=exc.output)
            return WorkflowExecutionResult(
                run_id=run_id,
                status="INTERRUPTED",
                output=exc.output,
                variable_scopes=self._last_variable_scopes,
            )
        except Exception as exc:
            self._repository.finish_run(run_id, "FAILED", output={}, error=str(exc))
            raise

    def resume(
        self,
        workflow_id: int,
        run_id: int,
        pending_node_key: str,
        input_data: dict[str, Any],
        node_outputs: dict[str, Any],
        variable_scopes: dict[str, Any] | None = None,
    ) -> WorkflowExecutionResult:
        workflow = self._repository.get(workflow_id)
        if workflow is None:
            raise WorkflowExecutionError("Workflow not found")
        context = ExecutionContext()
        if isinstance(variable_scopes, dict):
            context.load_scopes(variable_scopes)
        for node_key, output in node_outputs.items():
            if isinstance(output, Mapping):
                context.set_output(str(node_key), dict(output))
        context.set_output("start", input_data)
        nodes = self._repository.list_nodes(workflow_id)
        edges = self._repository.list_edges(workflow_id)
        self._last_variable_scopes = context.scopes_snapshot()
        try:
            output = self._run_graph(
                workflow_id,
                run_id,
                nodes,
                edges,
                input_data,
                start_node_key=pending_node_key,
                initial_context=context,
            )
            self._repository.finish_run(run_id, "SUCCEEDED", output=output)
            return WorkflowExecutionResult(
                run_id=run_id,
                status="SUCCEEDED",
                output=output,
                variable_scopes=self._last_variable_scopes,
            )
        except WorkflowInterrupt as exc:
            self._repository.finish_run(run_id, "INTERRUPTED", output=exc.output)
            return WorkflowExecutionResult(
                run_id=run_id,
                status="INTERRUPTED",
                output=exc.output,
                variable_scopes=self._last_variable_scopes,
            )
        except Exception as exc:
            self._repository.finish_run(run_id, "FAILED", output={}, error=str(exc))
            raise

    def run_node(
        self,
        workflow_id: int,
        node_key: str,
        input_data: dict[str, Any],
    ) -> WorkflowNodeExecutionResult:
        nodes = self._repository.list_nodes(workflow_id)
        node = next((item for item in nodes if str(item["node_key"]) == node_key), None)
        if node is None:
            raise WorkflowExecutionError("Workflow node not found")
        context = _fixture_context(input_data)
        started_at = perf_counter()
        output = self._execute_node(workflow_id, node, context, input_data)
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        return WorkflowNodeExecutionResult(
            node_key=node_key,
            status="SUCCEEDED",
            input=input_data,
            output=output,
            elapsed_ms=elapsed_ms,
        )

    def _run_graph(
        self,
        workflow_id: int,
        run_id: int,
        nodes: list[dict[str, Any]],
        edges: list[dict[str, Any]],
        input_data: dict[str, Any],
        start_node_key: str | None = None,
        initial_context: ExecutionContext | None = None,
    ) -> dict[str, Any]:
        node_map = {str(node["node_key"]): node for node in nodes}
        current = node_map.get(start_node_key) if start_node_key else next((node for node in nodes if node["type"] == "START"), None)
        if current is None:
            raise WorkflowExecutionError("Workflow START node not found")

        context = initial_context or ExecutionContext()
        _load_input_scopes(context, input_data)
        for _step in range(MAX_STEPS):
            context.set_local_values(_node_inputs(_config(current), context))
            try:
                node_run_id = self._repository.create_node_run(
                    run_id,
                    str(current["node_key"]),
                    str(current["type"]),
                    inputs=_node_run_inputs(current, context, input_data),
                )
                started_at = perf_counter()
                try:
                    output = self._execute_node(workflow_id, current, context, input_data)
                    context.set_output(str(current["node_key"]), output)
                    self._last_variable_scopes = context.scopes_snapshot()
                    elapsed_ms = int((perf_counter() - started_at) * 1000)
                    self._repository.finish_node_run(node_run_id, "SUCCEEDED", outputs=output, elapsed_ms=elapsed_ms)
                except WorkflowInterrupt as exc:
                    self._last_variable_scopes = context.scopes_snapshot()
                    elapsed_ms = int((perf_counter() - started_at) * 1000)
                    self._repository.finish_node_run(node_run_id, "INTERRUPTED", outputs=exc.output, elapsed_ms=elapsed_ms)
                    raise
                except Exception as exc:
                    elapsed_ms = int((perf_counter() - started_at) * 1000)
                    self._repository.finish_node_run(node_run_id, "FAILED", outputs={}, error=str(exc), elapsed_ms=elapsed_ms)
                    raise

                if current["type"] == "END":
                    return output

                next_node_key = self._next_node_key(current, edges, output)
                if next_node_key is None or next_node_key not in node_map:
                    raise WorkflowExecutionError(f"Next node not found after {current['node_key']}")
                current = node_map[next_node_key]
            finally:
                context.clear_local_values()

        raise WorkflowExecutionError("Workflow step limit exceeded")

    def _execute_node(
        self,
        workflow_id: int,
        node: dict[str, Any],
        context: ExecutionContext,
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        node_type = str(node["type"])
        if node_type == "START":
            return StartNodeExecutor(input_data).execute(node, context)
        if node_type == "LLM":
            return LlmNodeExecutor(self._llm_completer, self._knowledge_facade, self._mcp_tool_executor).execute(node, context)
        if node_type == "API_CALL":
            return ApiCallNodeExecutor(self._api_tool_executor).execute(node, context)
        if node_type == "TOOL_CALL":
            return ToolCallNodeExecutor(self._mcp_tool_executor, self._api_tool_executor).execute(node, context)
        if node_type == "EXECUTE_WORKFLOW":
            return ExecuteWorkflowNodeExecutor(
                self._repository,
                workflow_id,
                self._parent_workflow_ids,
                knowledge_facade=self._knowledge_facade,
                llm_completer=self._llm_completer,
                mcp_tool_executor=self._mcp_tool_executor,
                agent_invoker=self._agent_invoker,
                parent_agent_ids=self._parent_agent_ids,
            ).execute(node, context)
        if node_type == "AGENT_CALL":
            return AgentCallNodeExecutor(
                self._agent_invoker,
                parent_agent_ids=self._parent_agent_ids,
            ).execute(node, context)
        if node_type == "CODE":
            return CodeNodeExecutor().execute(node, context)
        if node_type == "TEXT_PROCESS":
            return TextProcessNodeExecutor().execute(node, context)
        if node_type == "JSON_PARSE":
            return JsonParseNodeExecutor().execute(node, context)
        if node_type == "VARIABLE_AGGREGATION":
            return VariableAggregationNodeExecutor().execute(node, context)
        if node_type == "VARIABLE_ASSIGN":
            return VariableAssignNodeExecutor().execute(node, context)
        if node_type == "INTENT_RECOGNITION":
            return IntentRecognitionNodeExecutor(self._llm_completer).execute(node, context)
        if node_type == "MESSAGE":
            return MessageNodeExecutor().execute(node, context)
        if node_type == "QUESTION":
            return QuestionNodeExecutor().execute(node, context)
        if node_type == "HUMAN_INPUT":
            return HumanInputNodeExecutor().execute(node, context)
        if node_type == "TRANSFER_TO_HUMAN":
            return TransferToHumanNodeExecutor(self._flow_type, self._handoff_service).execute(node, context)
        if node_type == "INFORMATION_COLLECTION":
            return InformationCollectionNodeExecutor(self._llm_completer).execute(node, context)
        if node_type == "KNOWLEDGE":
            return KnowledgeNodeExecutor(self._knowledge_facade).execute(node, context)
        if node_type == "CONDITION":
            return ConditionNodeExecutor().execute(node, context)
        if node_type == "END":
            return EndNodeExecutor().execute(node, context)
        raise WorkflowExecutionError(f"Unknown node type: {node_type}")

    def _next_node_key(
        self,
        node: dict[str, Any],
        edges: list[dict[str, Any]],
        output: dict[str, Any],
    ) -> str | None:
        node_key = str(node["node_key"])
        if node["type"] in {"CONDITION", "INTENT_RECOGNITION"}:
            branch_value = str(next(iter(output.values()), ""))
            return ConditionBranchPicker().pick(node_key, edges, branch_value)
        branch_value = output.get("route") or output.get("branch")
        if branch_value is not None:
            picked = ConditionBranchPicker().pick(node_key, edges, str(branch_value))
            if picked is not None:
                return picked
        edge = next(
            (
                item
                for item in edges
                if item["source_node_key"] == node_key and not item.get("condition_expr")
            ),
            None,
        )
        return str(edge["target_node_key"]) if edge else None


def _config(node: dict[str, Any]) -> dict[str, Any]:
    config = node.get("config")
    return dict(config) if isinstance(config, dict) else {}


def _validated_code_tree(code: str) -> ast.Module:
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise WorkflowExecutionError(f"CODE syntax error: {exc.msg}") from exc
    for node in ast.walk(tree):
        if isinstance(node, CodeNodeExecutor._blocked_nodes):
            raise WorkflowExecutionError("CODE node cannot import modules or mutate outer scope")
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in CodeNodeExecutor._blocked_call_names:
                raise WorkflowExecutionError(f"CODE node cannot call {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr.startswith("__"):
                raise WorkflowExecutionError("CODE node cannot access dunder attributes")
        if isinstance(node, ast.Attribute) and node.attr.startswith("__"):
            raise WorkflowExecutionError("CODE node cannot access dunder attributes")
        if isinstance(node, ast.Name) and node.id.startswith("__"):
            raise WorkflowExecutionError("CODE node cannot access dunder names")
    return tree


def _code_timeout_seconds(config: Mapping[str, Any]) -> float:
    raw_timeout = config.get("timeout", 60)
    try:
        timeout = float(raw_timeout)
    except (TypeError, ValueError):
        timeout = 60.0
    return min(max(timeout, 0.1), 60.0)


def _node_inputs(config: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
    inputs = context.get_output("start")
    parameters = config.get("inputParameters")
    if not isinstance(parameters, list):
        return inputs
    for item in parameters:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        value = item.get("value")
        if str(item.get("valueMode") or "reference") == "literal":
            inputs[name] = value
        else:
            inputs[name] = context.render(str(value or ""))
    return inputs


def _render_node_local_template(template: str, context: ExecutionContext, local_values: Mapping[str, Any]) -> str:
    return _render_local_template(context.render(template), local_values)


def _render_llm_prompts(config: dict[str, Any], context: ExecutionContext, local_inputs: Mapping[str, Any]) -> tuple[str, str]:
    system_prompt = _render_node_local_template(str(config.get("systemPrompt") or ""), context, local_inputs).strip()
    user_prompt = _render_node_local_template(str(config.get("prompt") or ""), context, local_inputs).strip()
    return system_prompt, user_prompt


def _node_run_inputs(node: Mapping[str, Any], context: ExecutionContext, input_data: dict[str, Any]) -> dict[str, Any]:
    config = _config(dict(node))
    node_type = str(node.get("type") or "")
    snapshot: dict[str, Any] = {
        "nodeKey": str(node.get("node_key") or node.get("nodeKey") or ""),
        "nodeType": node_type,
        "name": str(node.get("name") or ""),
        "config": _debug_config(config),
        "runtimeInput": dict(input_data),
        "scopes": context.scopes_snapshot(),
        "rendered": {},
    }
    rendered: dict[str, Any] = {}
    if node_type == "LLM":
        prompt = context.render(str(config.get("prompt") or ""))
        rendered["prompt"] = prompt
        if config.get("systemPrompt") is not None:
            rendered["systemPrompt"] = context.render(str(config.get("systemPrompt") or ""))
    elif node_type == "INTENT_RECOGNITION":
        text = context.render(str(config.get("inputSource") or config.get("input") or "{{start.sys.query}}"))
        history = _history_context(config, context)
        rendered["inputText"] = f"{' '.join(history)} {text}".strip() if history else text
        rendered["intents"] = [
            {"key": item.get("key"), "name": item.get("name"), "description": item.get("description")}
            for item in _intent_items(config)
        ]
    elif node_type == "INFORMATION_COLLECTION":
        fields = _collection_fields(config)
        rendered["inputText"] = _collection_input_text(config, context, str(node.get("node_key") or ""))
        rendered["currentTurnInput"] = _collection_current_turn_text(config, context, str(node.get("node_key") or ""))
        rendered["previousState"] = _collection_previous_state(config, context, str(node.get("node_key") or ""))
        rendered["fields"] = [
            {
                "name": field.get("name"),
                "description": field.get("description"),
                "required": field.get("required") is True,
                "targetScope": field.get("targetScope") or field.get("target_scope"),
                "targetVariable": field.get("targetVariable") or field.get("target_variable"),
                "historyMode": field.get("historyMode") or field.get("history_mode"),
            }
            for field in fields
        ]
    elif node_type == "QUESTION":
        rendered["question"] = context.render(str(config.get("question") or config.get("content") or ""))
    elif node_type == "MESSAGE":
        rendered["content"] = context.render(str(config.get("content") or config.get("message") or ""))
    elif node_type == "END":
        if "output" in config:
            rendered["output"] = context.render(str(config.get("output") or ""))
        rendered["declaredOutput"] = _declared_end_output(config, context)
    elif node_type in {"API_CALL", "TOOL_CALL", "EXECUTE_WORKFLOW", "AGENT_CALL"}:
        rendered["arguments"] = _mapped_arguments(config, context)
    elif node_type in {"TEXT_PROCESS", "JSON_PARSE", "VARIABLE_ASSIGN"}:
        rendered["source"] = _source_value(config, context)
    elif node_type == "VARIABLE_AGGREGATION":
        rendered["sources"] = _aggregation_sources(config, context)
        rendered["groups"] = _aggregation_groups(config, context)
    snapshot["rendered"] = rendered
    return snapshot


def _debug_config(config: Mapping[str, Any]) -> dict[str, Any]:
    blocked_keys = {"apiKey", "api_key", "authorization", "token", "secret", "password"}
    output: dict[str, Any] = {}
    for key, value in config.items():
        key_text = str(key)
        if key_text in blocked_keys or key_text.lower() in blocked_keys:
            output[key_text] = "***"
            continue
        output[key_text] = value
    return output


def _declared_output(values: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    parameters = config.get("outputParameters")
    if not isinstance(parameters, list) or not parameters:
        return values
    output: dict[str, Any] = {}
    for item in parameters:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if name:
            output[name] = values.get(name)
    for control_key in ("route", "branch"):
        if control_key in values and control_key not in output:
            output[control_key] = values[control_key]
    return output


def _declared_output_or_all(values: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    parameters = config.get("outputParameters")
    if not isinstance(parameters, list) or not parameters:
        return values
    return _declared_output(values, config)


def _declared_end_output(config: dict[str, Any], context: ExecutionContext) -> dict[str, Any]:
    parameters = config.get("outputParameters")
    if not isinstance(parameters, list):
        return {}
    output: dict[str, Any] = {}
    for item in parameters:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or "").strip()
        if not name:
            continue
        if "value" in item or "valueMode" in item:
            value = item.get("value")
            if str(item.get("valueMode") or "reference") == "literal":
                output[name] = value
            else:
                output[name] = context.render(str(value or ""))
        else:
            output[name] = context.find_value(name)
    return output


def _render_local_template(template: str, values: Mapping[str, Any]) -> str:
    def replace(match: re.Match[str]) -> str:
        value = values.get(match.group(1))
        return "" if value is None else str(value)

    return _LOCAL_TEMPLATE_PATTERN.sub(replace, template)


def _llm_stream_events(config: dict[str, Any], node_key: str, content: str) -> list[dict[str, Any]]:
    stream_output = str(config.get("streamOutput") or "inherit").lower()
    events: list[dict[str, Any]] = []
    if stream_output in {"enabled", "true", "1", "inherit"}:
        events.append({"type": "llm_delta", "nodeKey": node_key, "content": content})
    events.append({"type": "message_done", "nodeKey": node_key, "content": content})
    return events


def _agent_stream_events(config: dict[str, Any], node_key: str, content: str) -> list[dict[str, Any]]:
    stream_output = str(config.get("streamOutput") or "inherit").lower()
    events: list[dict[str, Any]] = []
    if stream_output in {"enabled", "true", "1", "inherit"}:
        events.append({"type": "agent_delta", "nodeKey": node_key, "content": content})
    events.append({"type": "message_done", "nodeKey": node_key, "content": content})
    return events


def _debug_extra_from_completer(completer: WorkflowLlmCompleter | None) -> dict[str, Any]:
    if completer is None or not hasattr(completer, "consume_last_call_debug"):
        return {}
    raw_debug = completer.consume_last_call_debug()  # type: ignore[attr-defined]
    if not isinstance(raw_debug, Mapping) or not raw_debug:
        return {}
    debug = dict(raw_debug)
    output: dict[str, Any] = {"__debug": {"llm": debug}}
    usage = debug.get("usage")
    if isinstance(usage, Mapping):
        output["__usage"] = {
            "inputTokens": _non_negative_int(usage.get("inputTokens"), 0),
            "outputTokens": _non_negative_int(usage.get("outputTokens"), 0),
            "totalTokens": _non_negative_int(
                usage.get("totalTokens"),
                _non_negative_int(usage.get("inputTokens"), 0) + _non_negative_int(usage.get("outputTokens"), 0),
            ),
            "estimated": bool(usage.get("estimated")),
        }
    return output


def _node_usage_event(node_key: str, usage: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "type": "node_usage",
        "nodeKey": node_key,
        "inputTokens": _non_negative_int(usage.get("inputTokens"), 0),
        "outputTokens": _non_negative_int(usage.get("outputTokens"), 0),
        "totalTokens": _non_negative_int(
            usage.get("totalTokens"),
            _non_negative_int(usage.get("inputTokens"), 0) + _non_negative_int(usage.get("outputTokens"), 0),
        ),
    }


def _first_output_name(config: dict[str, Any], default: str) -> str:
    parameters = config.get("outputParameters")
    if isinstance(parameters, list):
        for item in parameters:
            if isinstance(item, Mapping):
                name = str(item.get("name") or "").strip()
                if name:
                    return name
    return str(config.get("outputVariable") or default)


def _source_value(config: dict[str, Any], context: ExecutionContext) -> Any:
    if "source" in config:
        return context.render(str(config.get("source") or ""))
    if "sourceValue" in config:
        value = config.get("sourceValue")
        return context.render(value) if isinstance(value, str) else value
    if "input" in config:
        value = config.get("input")
        return context.render(value) if isinstance(value, str) else value
    return ""


def _assignment_source_value(
    config: dict[str, Any],
    context: ExecutionContext,
    scope: str,
    variable_name: str,
) -> Any:
    mode = str(config.get("sourceValueMode") or config.get("valueMode") or config.get("assignmentMode") or "").strip().lower()
    if mode in {"operation", "calculation", "compute", "operator"}:
        return _assignment_operation_value(config, context, scope, variable_name)
    return _source_value(config, context)


def _assignment_operation_value(
    config: dict[str, Any],
    context: ExecutionContext,
    scope: str,
    variable_name: str,
) -> int | float:
    operation = str(config.get("operation") or config.get("operator") or "add").strip().lower()
    raw_operand = config.get("operand")
    if raw_operand is None:
        raw_operand = config.get("source")
    if raw_operand is None:
        raw_operand = 1 if operation in {"increment", "inc", "decrement", "dec"} else 0
    operand = context.render(raw_operand) if isinstance(raw_operand, str) else raw_operand
    current = context.get_scope(scope).get(variable_name, 0)
    current_number = _assignment_number(current, f"{scope}.{variable_name}")
    operand_number = _assignment_number(operand, "operand")

    if operation in {"add", "plus", "increment", "inc"}:
        return _normalized_assignment_number(current_number + operand_number)
    if operation in {"subtract", "minus", "decrement", "dec"}:
        return _normalized_assignment_number(current_number - operand_number)
    if operation in {"multiply", "mul", "times"}:
        return _normalized_assignment_number(current_number * operand_number)
    if operation in {"divide", "div"}:
        if operand_number == 0:
            raise WorkflowExecutionError("VARIABLE_ASSIGN operation divide requires non-zero operand")
        return _normalized_assignment_number(current_number / operand_number)
    raise WorkflowExecutionError(f"Unsupported VARIABLE_ASSIGN operation: {operation}")


def _assignment_number(value: Any, label: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"VARIABLE_ASSIGN operation requires numeric {label}: {value}") from exc


def _normalized_assignment_number(value: float) -> int | float:
    return int(value) if value.is_integer() else value


def _normalized_resource_type(value: Any) -> str:
    return str(value or "").strip().upper().replace("-", "_")


def _tool_server_ids(config: dict[str, Any]) -> list[int]:
    raw_ids = _maybe_json(config.get("serverIds") or config.get("server_ids"))
    ids: list[int] = []
    if isinstance(raw_ids, list):
        for raw_id in raw_ids:
            try:
                ids.append(int(raw_id))
            except (TypeError, ValueError):
                continue
    elif raw_ids is not None:
        try:
            ids.append(int(raw_ids))
        except (TypeError, ValueError):
            pass

    resource_id = str(config.get("resourceId") or config.get("resource_id") or "")
    match = re.match(r"^mcp:(\d+)(?::[^:]+)?$", resource_id)
    if match:
        ids.append(int(match.group(1)))
    return list(dict.fromkeys(ids))


def _tool_call_arguments(config: dict[str, Any], context: ExecutionContext) -> dict[str, object]:
    raw_mappings = _maybe_json(config.get("inputMappings") or config.get("argumentMappings") or config.get("inputParameters") or [])
    if not isinstance(raw_mappings, list):
        raw_mappings = []
    arguments: dict[str, object] = {}
    for item in raw_mappings:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("key") or item.get("parameter") or "").strip()
        if not name:
            continue
        value = _tool_mapping_value(item, context)
        required = item.get("required") is True
        if required and not _not_empty(value):
            raise WorkflowExecutionError(f"{name} is required")
        if _not_empty(value):
            arguments[name] = value
    return arguments


def _mapped_arguments(config: dict[str, Any], context: ExecutionContext) -> dict[str, object]:
    raw_mappings = _maybe_json(config.get("inputMappings") or config.get("inputParameters") or [])
    if not isinstance(raw_mappings, list):
        raw_mappings = []
    arguments: dict[str, object] = {}
    for item in raw_mappings:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("key") or item.get("target") or "").strip()
        if not name:
            continue
        value = _tool_mapping_value(item, context)
        required = item.get("required") is True
        if required and not _not_empty(value):
            raise WorkflowExecutionError(f"{name} is required")
        if _not_empty(value):
            arguments[name] = value
    return arguments


def _mapped_output(config: dict[str, Any], nested_output: dict[str, Any]) -> dict[str, Any]:
    raw_mappings = _maybe_json(config.get("outputMappings") or config.get("outputParametersMapping") or [])
    if not isinstance(raw_mappings, list) or not raw_mappings:
        return dict(nested_output)
    output: dict[str, Any] = {}
    for item in raw_mappings:
        if not isinstance(item, Mapping):
            continue
        source = str(item.get("source") or item.get("from") or item.get("name") or "").strip()
        target = str(item.get("target") or item.get("to") or source).strip()
        if not source or not target:
            continue
        output[target] = _json_path_value(nested_output, source)
    return output


def _target_workflow_id(config: dict[str, Any]) -> int | None:
    raw_id = config.get("targetWorkflowId") or config.get("target_workflow_id") or config.get("workflowId")
    if raw_id is None or str(raw_id).strip() == "":
        resource_id = str(config.get("resourceId") or config.get("resource_id") or "")
        match = re.match(r"^(?:workflow|subworkflow):(\d+)$", resource_id)
        raw_id = match.group(1) if match else None
    if raw_id is None or str(raw_id).strip() == "":
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError("EXECUTE_WORKFLOW targetWorkflowId must be numeric") from exc


def _target_agent_id(config: dict[str, Any]) -> int | None:
    raw_id = config.get("targetAgentId") or config.get("target_agent_id") or config.get("agentId")
    if raw_id is None or str(raw_id).strip() == "":
        resource_id = str(config.get("resourceId") or config.get("resource_id") or "")
        match = re.match(r"^agent:(\d+)$", resource_id)
        raw_id = match.group(1) if match else None
    if raw_id is None or str(raw_id).strip() == "":
        return None
    try:
        return int(raw_id)
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError("AGENT_CALL targetAgentId must be numeric") from exc


def _agent_call_message(config: dict[str, Any], mapped_input: dict[str, object], context: ExecutionContext) -> str:
    mapped_message = mapped_input.get("message")
    if mapped_message is not None and str(mapped_message).strip():
        return str(mapped_message)
    for key in ("messageTemplate", "message", "prompt"):
        if config.get(key) is not None and str(config.get(key)).strip():
            return context.render(str(config[key]))
    query = mapped_input.get("query")
    if query is not None and str(query).strip():
        return str(query)
    start_values = context.get_output("start")
    for key in ("sys.query", "USER_INPUT", "userMessage", "message", "query"):
        value = start_values.get(key)
        if value is not None and str(value).strip():
            return str(value)
    raise WorkflowExecutionError("AGENT_CALL requires message input")


def _agent_call_history(config: dict[str, Any], context: ExecutionContext) -> list[dict[str, Any]]:
    mode = str(config.get("historyMode") or "none").lower()
    if mode not in {"include", "all", "recent"}:
        return []
    start_values = context.get_output("start")
    raw_history = start_values.get("history") or start_values.get("conversationHistory")
    if not isinstance(raw_history, list):
        return []
    history: list[dict[str, Any]] = []
    for item in raw_history:
        if not isinstance(item, Mapping):
            continue
        role = str(item.get("role") or "user")
        content = str(item.get("content") or "")
        if content:
            history.append({"role": role, "content": content})
    return history


def _agent_call_timeout_ms(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = 30_000
    if parsed <= 0:
        raise WorkflowExecutionError("AGENT_CALL timed out")
    return parsed


def _format_agent_history(history: list[dict[str, Any]]) -> str:
    return "\n".join(f"- {item.get('role', 'user')}: {item.get('content', '')}" for item in history)


def _maybe_json(value: Any) -> Any:
    if isinstance(value, str) and value.strip():
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return value
    return value


def _tool_mapping_value(item: Mapping[str, Any], context: ExecutionContext) -> object:
    value = item.get("value")
    if str(item.get("valueMode") or "reference") == "literal":
        if isinstance(value, str) and str(item.get("type") or "").lower() in {"object", "array"}:
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value  # type: ignore[return-value]
    return context.render(str(value or ""))


def _resource_execution_policy(config: dict[str, Any], tool_name: str) -> ResourceExecutionPolicy:
    timeout_ms = _positive_int(config.get("timeoutMs") or config.get("timeout_ms"), default=30_000)
    retry_count = _non_negative_int(config.get("retryCount") or config.get("retry_count"), default=0)
    error_behavior = str(config.get("errorBehavior") or config.get("error_behavior") or "fail").strip().lower()
    if error_behavior not in {"fail", "continue", "branch"}:
        raise WorkflowExecutionError(f"Unsupported resource errorBehavior: {error_behavior}")
    tool_policies = config.get("toolPolicies")
    tool_policy = tool_policies.get(tool_name) if isinstance(tool_policies, Mapping) else {}
    allow_write = _truthy(config.get("allowWrite") or config.get("allow_write") or config.get("writeAllowed"))
    if isinstance(tool_policy, Mapping):
        allow_write = allow_write or _truthy(tool_policy.get("allowWrite") or tool_policy.get("allow_write"))
    return ResourceExecutionPolicy(
        timeout_ms=timeout_ms,
        retry_count=retry_count,
        error_behavior=error_behavior,
        allow_write=allow_write,
    )


def _tool_result_error(result: Any, elapsed_ms: int, timeout_ms: int, tool_name: str) -> str:
    if elapsed_ms > timeout_ms:
        return f"Tool call timed out: {tool_name}"
    if result.success:
        return ""
    return str(result.error_message or f"Tool call failed: {tool_name}")


def _write_capable_tool(tool_name: str) -> bool:
    lowered = tool_name.lower()
    return lowered.startswith(("refund_", "create_", "update_", "delete_"))


def _non_negative_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on", "allow", "allowed"}


def _field_map(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = config.get("fieldMap") or config.get("mappings") or []
    if not isinstance(raw, list):
        return []
    return [dict(item) for item in raw if isinstance(item, Mapping)]


def _aggregation_sources(config: dict[str, Any], context: ExecutionContext) -> list[dict[str, Any]]:
    raw = config.get("sources") or config.get("inputSources") or []
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("label") or "").strip()
        value = item.get("value")
        if isinstance(value, str):
            value = context.render(value)
        result.append({"name": name, "value": value})
    return result


def _aggregation_groups(config: dict[str, Any], context: ExecutionContext) -> list[dict[str, Any]]:
    raw = config.get("groups") or config.get("mergeGroups")
    inputs = config.get("inputs")
    if raw is None and isinstance(inputs, Mapping):
        raw = inputs.get("mergeGroups")
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for group_index, group in enumerate(raw):
        if not isinstance(group, Mapping):
            continue
        name = str(group.get("name") or group.get("groupName") or f"Group{group_index + 1}").strip()
        if not name:
            continue
        raw_variables = group.get("variables") or group.get("values") or []
        if not isinstance(raw_variables, list):
            raw_variables = []
        variables: list[dict[str, Any]] = []
        for item in raw_variables:
            value = item
            if isinstance(item, Mapping):
                value = item.get("value")
            if isinstance(value, str):
                value = context.render(value)
            variables.append({"value": value})
        result.append({"name": name, "variables": variables})
    return result


def _render_optional(value: Any, context: ExecutionContext) -> Any:
    if value is None:
        return None
    return context.render(value) if isinstance(value, str) else value


def _not_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return value != ""
    if isinstance(value, (list, tuple, dict, set)):
        return len(value) > 0
    return True


def _resume_payload(context: ExecutionContext, node_key: str) -> Any:
    start_values = context.get_output("start")
    resume = start_values.get("resume")
    if isinstance(resume, Mapping) and node_key in resume:
        return resume[node_key]
    dotted_prefix = f"resume.{node_key}."
    payload: dict[str, Any] = {}
    for key, value in start_values.items():
        key_text = str(key)
        if key_text.startswith(dotted_prefix):
            payload[key_text.removeprefix(dotted_prefix)] = value
    if payload:
        return payload
    return None


def _collection_fields(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = config.get("fields") or config.get("slots") or []
    if isinstance(raw, str) and raw.strip():
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return []
    if not isinstance(raw, list):
        return []
    fields: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("key") or "").strip()
        if not name:
            continue
        field = dict(item)
        field["name"] = name
        fields.append(field)
    return fields


def _collection_previous_state(config: dict[str, Any], context: ExecutionContext, node_key: str) -> dict[str, Any]:
    resume = _resume_payload(context, node_key)
    candidates: list[Any] = []
    if isinstance(resume, Mapping):
        candidates.extend([resume.get("collected"), resume.get("state"), resume.get("values")])
    start_values = context.get_output("start")
    collection_key = str(config.get("collectionKey") or "collected")
    candidates.extend([start_values.get(collection_key), start_values.get("collected")])
    for candidate in candidates:
        if isinstance(candidate, Mapping):
            return dict(candidate)
    return {}


def _collection_input_text(config: dict[str, Any], context: ExecutionContext, node_key: str) -> str:
    parts: list[str] = []
    history = _history_context(config, context)
    if history:
        parts.extend(history)
    current_turn_text = _collection_current_turn_text(config, context, node_key)
    if current_turn_text:
        parts.append(current_turn_text)
    return "\n".join(parts)


def _collection_current_turn_text(config: dict[str, Any], context: ExecutionContext, node_key: str) -> str:
    parts: list[str] = []
    configured = context.render(str(config.get("inputSource") or config.get("input") or "{{start.sys.query}}"))
    if configured:
        parts.append(configured)
    resume = _resume_payload(context, node_key)
    if isinstance(resume, Mapping):
        answer = resume.get("answer") or resume.get("message") or resume.get("text")
        if answer is not None:
            parts.append(str(answer))
    elif resume is not None:
        parts.append(str(resume))
    return "\n".join(parts)


def _collection_field_current_turn_only(field: Mapping[str, Any]) -> bool:
    mode = str(field.get("historyMode") or field.get("history_mode") or "").strip().lower()
    return mode in {"current", "current_only", "current_turn", "current_turn_only", "no_history"}


def _collection_round(context: ExecutionContext, node_key: str) -> int:
    resume = _resume_payload(context, node_key)
    if isinstance(resume, Mapping):
        return _positive_int(resume.get("round") or resume.get("turn"), default=0)
    start_values = context.get_output("start")
    return _positive_int(start_values.get("sys.round") or start_values.get("round"), default=0)


def _collection_followup(
    config: dict[str, Any],
    missing: list[str],
    fields: list[dict[str, Any]],
    collected: dict[str, Any],
) -> str:
    template = str(config.get("followupTemplate") or config.get("followup") or "").strip()
    joined = ", ".join(missing)
    if template:
        missing_labels = _join_collection_labels(_collection_field_labels(fields, missing))
        collected_names = [
            str(field["name"])
            for field in fields
            if str(field["name"]) not in set(missing) and _collection_value_present(collected.get(str(field["name"])))
        ]
        collected_labels = _join_collection_labels(_collection_field_labels(fields, collected_names))
        collected_notice = f"已记录{collected_labels}，" if collected_labels else ""
        return (
            template.replace("{{missing}}", joined)
            .replace("{{missing_labels}}", missing_labels or joined)
            .replace("{{collected_labels}}", collected_labels)
            .replace("{{collected_notice}}", collected_notice)
        )
    return f"请补充 {joined}"


def _collection_field_labels(fields: list[dict[str, Any]], names: list[str]) -> list[str]:
    labels_by_name = {
        str(field["name"]): str(field.get("description") or field["name"]).strip()
        for field in fields
        if "name" in field
    }
    return [labels_by_name.get(name, name) for name in names]


def _join_collection_labels(labels: list[str]) -> str:
    return "、".join(label for label in labels if label)


def _collection_value_present(value: Any) -> bool:
    if not _not_empty(value):
        return False
    if not isinstance(value, str):
        return True
    normalized = value.strip().lower()
    return normalized not in {
        "未指定",
        "未知",
        "不知道",
        "未提供",
        "未填写",
        "不详",
        "待定",
        "无",
        "没有",
        "none",
        "null",
        "n/a",
        "na",
        "-",
    }


def _write_collection_targets(
    fields: list[dict[str, Any]],
    collected: dict[str, Any],
    context: ExecutionContext,
) -> None:
    for field_spec in fields:
        name = str(field_spec.get("name") or "")
        if name not in collected:
            continue
        scope = str(field_spec.get("targetScope") or "").strip()
        variable = str(field_spec.get("targetVariable") or "").strip()
        if not scope or not variable:
            continue
        try:
            context.set_scope_value(scope, variable, collected[name], "set")
        except ValueError as exc:
            raise WorkflowExecutionError(str(exc)) from exc


def _extract_collection_values_fake(text: str, fields: list[dict[str, Any]]) -> dict[str, Any]:
    values: dict[str, Any] = {}
    for field_spec in fields:
        name = str(field_spec["name"])
        field_type = str(field_spec.get("type") or "string").lower()
        description = str(field_spec.get("description") or "")
        label = f"{name} {description}".lower()
        value: Any = None
        if any(term in label for term in ["phone", "mobile", "手机号", "手机", "电话"]):
            match = re.search(r"(?<!\d)(1[3-9]\d{9})(?!\d)", text)
            value = match.group(1) if match else None
        elif any(term in label for term in ["email", "邮箱", "mail"]):
            match = re.search(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text)
            value = match.group(0) if match else None
        elif any(term in label for term in ["name", "姓名", "名字"]):
            match = re.search(
                r"(?:我叫|姓名|名字|name\s+is)\s*[:：]?\s*([A-Za-z\u4e00-\u9fff][A-Za-z0-9_\-\u4e00-\u9fff]*)",
                text,
                flags=re.IGNORECASE,
            )
            value = match.group(1) if match else None
        else:
            value = _extract_labeled_value(text, name) or _extract_labeled_value(text, description)
        if value is None:
            continue
        if field_type in {"number", "integer", "float"}:
            try:
                value = float(value) if field_type == "float" else int(float(value))
            except (TypeError, ValueError):
                continue
        elif field_type == "boolean":
            normalized = str(value).strip().lower()
            value = normalized in {"true", "1", "yes", "y", "是", "同意"}
        values[name] = value
    return values


def _extract_labeled_value(text: str, label: str) -> str | None:
    cleaned = label.strip()
    if not cleaned:
        return None
    pattern = rf"{re.escape(cleaned)}\s*[:：]\s*([^\s,，。;；]+)"
    match = re.search(pattern, text, flags=re.IGNORECASE)
    return match.group(1) if match else None


def _extract_collection_values_llm(
    completer: WorkflowLlmCompleter,
    text: str,
    fields: list[dict[str, Any]],
    config: dict[str, Any],
) -> dict[str, Any]:
    field_brief = [
        {
            "name": field.get("name"),
            "type": field.get("type") or "string",
            "required": field.get("required") is True,
            "description": field.get("description") or "",
            "historyMode": field.get("historyMode") or field.get("history_mode") or "",
            "extractionHint": field.get("extractionHint") or field.get("extraction_hint") or "",
        }
        for field in fields
    ]
    prompt = (
        "你是信息抽取器。只输出 JSON object，不要输出解释、Markdown 或代码块。"
        "JSON key 必须优先使用字段 name；如果无法使用 name，也可以使用字段 description。"
        "未知值不要编造，直接省略。\n"
        "示例：字段 destination/目的城市 与 budget/预算金额，文本“去上海，预算5000元”应输出 "
        "{\"destination\":\"上海\",\"budget\":\"5000\"}。\n"
        f"Fields: {json.dumps(field_brief, ensure_ascii=False)}\n"
        f"Message:\n{text}"
    )
    raw = completer.complete_prompt(prompt, {**_llm_options(config), "responseFormat": "JSON"})
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if not match:
            return {}
        try:
            parsed = json.loads(match.group(0))
        except json.JSONDecodeError:
            return {}
    if not isinstance(parsed, Mapping):
        return {}
    aliases: dict[str, str] = {}
    for field_spec in fields:
        name = str(field_spec["name"])
        aliases[name] = name
        description = str(field_spec.get("description") or "").strip()
        if description:
            aliases[description] = name
    output: dict[str, Any] = {}
    for key, value in parsed.items():
        target_name = aliases.get(str(key).strip())
        if target_name and _collection_value_present(value):
            output[target_name] = value
    return output


def _intent_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    raw = config.get("intents") or []
    if not isinstance(raw, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, Mapping):
            continue
        key = str(item.get("key") or item.get("id") or item.get("name") or "").strip()
        if not key:
            continue
        copied = dict(item)
        copied["key"] = key
        result.append(copied)
    return result


def _classify_intent_fake(text: str, intents: list[dict[str, Any]], default_intent: str) -> dict[str, Any]:
    normalized_text = text.lower()
    best_key = default_intent
    best_score = 0
    best_term = ""
    for intent in intents:
        terms = _intent_terms(intent)
        matched_terms = [term for term in terms if term and term.lower() in normalized_text]
        score = len(set(matched_terms))
        if score > best_score:
            best_score = score
            best_key = str(intent["key"])
            best_term = matched_terms[0]
    if best_score <= 0:
        return {"intent": default_intent, "confidence": 0.0, "reason": "no intent matched"}
    confidence = min(1.0, max(0.5, best_score / 3))
    return {"intent": best_key, "confidence": confidence, "reason": f"matched term: {best_term}"}


def _intent_terms(intent: Mapping[str, Any]) -> list[str]:
    terms: list[str] = [str(intent.get("key") or ""), str(intent.get("name") or "")]
    examples = intent.get("examples") or []
    if isinstance(examples, list):
        terms.extend(str(item) for item in examples)
    description = str(intent.get("description") or "")
    if description:
        terms.append(description)
        terms.extend(re.findall(r"[A-Za-z0-9_]+|[\u4e00-\u9fff]{2,}", description))
    return [term.strip() for term in terms if term and term.strip()]


def _json_path_value(value: Any, path: str) -> Any:
    if not path or path == "$":
        return value
    parts = _json_path_parts(path)
    if not parts:
        return None
    current = value
    for part in parts:
        if part == "":
            continue
        if isinstance(current, Mapping):
            current = current.get(part)
            continue
        if isinstance(current, list) and part.isdigit():
            index = int(part)
            current = current[index] if index < len(current) else None
            continue
        return None
    return current


def _json_path_parts(path: str) -> list[str]:
    normalized = path.strip()
    if normalized == "$":
        return []
    if normalized.startswith("$"):
        normalized = normalized[1:]

    parts: list[str] = []
    index = 0
    while index < len(normalized):
        char = normalized[index]
        if char == ".":
            index += 1
            continue
        if char == "[":
            end = normalized.find("]", index + 1)
            if end < 0:
                return []
            token = normalized[index + 1:end].strip()
            if len(token) >= 2 and token[0] in {"'", '"'} and token[-1] == token[0]:
                token = token[1:-1]
            parts.append(token)
            index = end + 1
            continue

        end = index
        while end < len(normalized) and normalized[end] not in ".[":
            end += 1
        token = normalized[index:end].strip()
        if token:
            parts.append(token)
        index = end
    return parts


def _resource_items(config: dict[str, Any]) -> list[dict[str, Any]]:
    resources = config.get("resources") or config.get("skillResources") or []
    if not isinstance(resources, list):
        return []
    return [
        dict(resource)
        for resource in resources
        if isinstance(resource, dict) and resource.get("enabled") is not False
    ]


def _callable_tool_resources(config: dict[str, Any]) -> list[dict[str, Any]]:
    if _tool_choice_mode(config) == "disabled":
        return []
    return [
        resource
        for resource in _resource_items(config)
        if _resource_type(resource) == "mcp"
    ]


def _tool_choice_mode(config: dict[str, Any]) -> str:
    return str(config.get("toolChoiceMode") or config.get("tool_choice") or "auto").strip().lower()


def _llm_tool_settings(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "toolChoiceMode": _tool_choice_mode(config),
        "maxToolRounds": _positive_int(config.get("maxToolRounds") or config.get("max_tool_rounds"), default=1),
        "toolResultMode": str(config.get("toolResultMode") or config.get("tool_result_mode") or "append").strip().lower(),
    }


def _callable_tool_server_ids(resources: list[dict[str, Any]]) -> list[int]:
    ids: list[int] = []
    for resource in resources:
        ids.extend(_tool_server_ids(resource))
    return list(dict.fromkeys(ids))


def _resource_type(resource: dict[str, Any]) -> str:
    raw_type = str(resource.get("type") or resource.get("resourceType") or "").strip().upper().replace("-", "_")
    if raw_type in {"KNOWLEDGE", "KNOWLEDGE_BASE", "KNOWLEDGE_BASES", "KNOWLEDGEBASE"}:
        return "knowledge"
    if raw_type in {"MCP", "MCP_TOOL", "MCP_TOOLS", "MCP_SERVER", "MCP_SERVER_TOOL", "TOOL"}:
        return "mcp"
    if raw_type in {"SUBWORKFLOW", "SUB_WORKFLOW", "WORKFLOW"}:
        return "subworkflow"
    return raw_type.lower() or "unknown"


def _resource_id(resource: dict[str, Any]) -> int | None:
    raw_id = resource.get("knowledgeBaseId") or resource.get("knowledge_base_id") or resource.get("resourceId") or resource.get("id")
    if raw_id is None or str(raw_id).strip() == "":
        return None
    return int(raw_id)


def _positive_int(value: Any, default: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _retrieval_mode(value: Any) -> str:
    normalized = str(value or "auto").strip().lower()
    return normalized if normalized in {"auto", "hybrid", "semantic", "keyword", "faq"} else "auto"


def _score_threshold(value: Any) -> float:
    try:
        parsed = float(value or 0)
    except (TypeError, ValueError):
        return 0.0
    return min(max(parsed, 0.0), 1.0)


def _bool_setting(value: Any, *, default: bool) -> bool:
    if value is None:
        return default
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


def _execute_workflow_max_depth(value: Any, default: int = 3) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed >= 0 else default


def _positive_float(value: Any, default: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if parsed > 0 else default


def _render_headers(raw_headers: Any, context: ExecutionContext) -> dict[str, str]:
    if isinstance(raw_headers, str) and raw_headers.strip():
        rendered = context.render(raw_headers)
        try:
            raw_headers = json.loads(rendered)
        except json.JSONDecodeError:
            return {}
    if isinstance(raw_headers, Mapping):
        return {
            str(key): context.render(str(value))
            for key, value in raw_headers.items()
            if str(key).strip()
        }
    if not isinstance(raw_headers, list):
        return {}
    headers: dict[str, str] = {}
    for item in raw_headers:
        if not isinstance(item, Mapping):
            continue
        name = str(item.get("name") or item.get("key") or "").strip()
        if not name:
            continue
        headers[name] = context.render(str(item.get("value") or ""))
    return headers


def _render_payload(value: Any, context: ExecutionContext) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        rendered = context.render(value)
        try:
            return json.loads(rendered)
        except json.JSONDecodeError:
            return rendered
    if isinstance(value, Mapping):
        return {str(key): _render_payload(item, context) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_payload(item, context) for item in value]
    return value


def _response_payload(response: httpx.Response) -> Any:
    content_type = response.headers.get("Content-Type", "")
    if "json" in content_type.lower():
        return response.json()
    text = response.text
    try:
        return response.json()
    except ValueError:
        return text


def _matched_condition_branch(config: dict[str, Any], context: ExecutionContext) -> str | None:
    branches = config.get("conditionBranches") or config.get("branches")
    if not isinstance(branches, list):
        return None
    for branch in branches:
        if not isinstance(branch, Mapping):
            continue
        conditions = branch.get("conditions") or []
        if not isinstance(conditions, list):
            continue
        logic = str(branch.get("logic") or "AND").upper()
        results = [_evaluate_condition(item, context) for item in conditions if isinstance(item, Mapping)]
        matched = bool(results) and (any(results) if logic == "OR" else all(results))
        if matched:
            return str(branch.get("key") or branch.get("id") or branch.get("value") or "")
    default_branch = config.get("defaultBranch") or config.get("default_branch")
    return str(default_branch) if default_branch is not None else None


def _evaluate_condition(condition: Mapping[str, Any], context: ExecutionContext) -> bool:
    left = _condition_operand_value(condition, ("left", "field"), context)
    operator = str(condition.get("operator") or "equals").lower()
    right = _condition_operand_value(condition, ("right", "value"), context)
    if operator in {"equals", "eq", "=="}:
        return left == right
    if operator in {"not_equals", "neq", "!="}:
        return left != right
    if operator in {"contains", "include"}:
        return right in left
    if operator in {"not_contains", "not_include"}:
        return right not in left
    if operator in {"greater_than", "gt", ">"}:
        return _number(left) > _number(right)
    if operator in {"greater_or_equal", "gte", ">="}:
        return _number(left) >= _number(right)
    if operator in {"less_than", "lt", "<"}:
        return _number(left) < _number(right)
    if operator in {"less_or_equal", "lte", "<="}:
        return _number(left) <= _number(right)
    if operator in {"length_greater_than", "length_gt", "len_gt"}:
        return len(left) > _number(right)
    if operator in {"length_greater_or_equal", "length_gte", "len_gte"}:
        return len(left) >= _number(right)
    if operator in {"length_less_than", "length_lt", "len_lt"}:
        return len(left) < _number(right)
    if operator in {"length_less_or_equal", "length_lte", "len_lte"}:
        return len(left) <= _number(right)
    if operator in {"is_empty", "empty"}:
        return _is_empty_value(left)
    if operator in {"is_not_empty", "not_empty"}:
        return not _is_empty_value(left)
    if operator in {"is_true", "true"}:
        return _truthy_condition_value(left)
    if operator in {"is_false", "false"}:
        return not _truthy_condition_value(left)
    raise WorkflowExecutionError(f"Unsupported condition operator: {operator}")


def _condition_operand_value(
    condition: Mapping[str, Any],
    keys: tuple[str, ...],
    context: ExecutionContext,
) -> str:
    raw: Any = ""
    for key in keys:
        if key in condition:
            raw = condition.get(key)
            break
    if isinstance(raw, Mapping):
        raw = raw.get("value") if "value" in raw else raw.get("reference", raw.get("literal", ""))
    return context.render(str(raw or ""))


def _number(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise WorkflowExecutionError(f"Condition value is not numeric: {value}") from exc


def _is_empty_value(value: Any) -> bool:
    text = str(value or "").strip()
    return text in {"", "[]", "{}"}


def _truthy_condition_value(value: Any) -> bool:
    text = str(value or "").strip().lower()
    if text in {"1", "true", "yes", "y", "on"}:
        return True
    if text in {"", "0", "false", "no", "n", "off", "none", "null"}:
        return False
    return bool(text)


def _llm_options(config: dict[str, Any]) -> dict[str, Any]:
    keys = {
        "model",
        "modelConfigId",
        "model_config_id",
        "systemPrompt",
        "temperature",
        "maxTokens",
        "max_tokens",
        "topP",
        "top_p",
        "frequencyPenalty",
        "frequency_penalty",
        "presencePenalty",
        "presence_penalty",
        "responseFormat",
        "response_format",
        "stopSequences",
        "stop",
        "seed",
        "toolChoiceMode",
        "maxToolRounds",
        "toolResultMode",
    }
    return {key: config[key] for key in keys if key in config}


def _fixture_context(input_data: dict[str, Any]) -> ExecutionContext:
    context = ExecutionContext()
    context.set_output("start", input_data)
    _load_input_scopes(context, input_data)
    for key, value in input_data.items():
        if isinstance(value, dict):
            context.set_output(str(key), value)
    return context


def _load_input_scopes(context: ExecutionContext, input_data: dict[str, Any]) -> None:
    scoped_prefixes = {"flow", "global", "conversation", "user", "channel", "sys"}
    for key, value in input_data.items():
        key_text = str(key)
        context.set_scope_value("input", key_text, value)
        context.set_scope_value("external", key_text, value)
        if "." in key_text:
            prefix, variable_name = key_text.split(".", 1)
            if prefix in scoped_prefixes and variable_name:
                context.set_scope_value(prefix, variable_name, value)
            continue
        if key_text in scoped_prefixes and isinstance(value, Mapping):
            for variable_name, item in value.items():
                context.set_scope_value(key_text, str(variable_name), item)


def _handoff_transcript(start_values: dict[str, Any]) -> list[dict[str, str]]:
    content = str(start_values.get("sys.query") or start_values.get("USER_INPUT") or start_values.get("userMessage") or "")
    return [{"role": "user", "content": content}] if content else []


def _history_context(config: dict[str, Any], context: ExecutionContext) -> list[str]:
    if str(config.get("includeHistory") or "").lower() not in {"1", "true", "yes", "on"}:
        return []
    start_values = context.get_output("start")
    raw_history = start_values.get("history") or start_values.get("conversationHistory") or []
    if not isinstance(raw_history, list):
        return []
    result: list[str] = []
    for item in raw_history[-10:]:
        if isinstance(item, dict):
            role = str(item.get("role") or "message")
            content = str(item.get("content") or "")
            if content:
                result.append(f"{role}: {content}")
        elif item is not None:
            result.append(str(item))
    return result
