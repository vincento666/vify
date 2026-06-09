from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any
import json
import re

import httpx

from app.core.errors import BizError, ErrorCode
from app.modules.workflow.infra.api_resource_repository import ApiResourceRepository
from app.modules.workflow.web.api_resource_schemas import (
    ApiResourceCreateRequest,
    ApiResourceTestCallRequest,
    ApiResourceUpdateRequest,
    ApiToolCreateRequest,
    format_datetime,
)


@dataclass(frozen=True)
class ApiResourceCallResult:
    success: bool
    result: Any
    elapsed_ms: int
    error_message: str
    response: dict[str, Any]
    evidence: dict[str, Any]


class ApiResourceService:
    def __init__(self, repository: ApiResourceRepository) -> None:
        self._repository = repository

    def list_resources(self, page: int, page_size: int, enabled: bool | None = None) -> dict[str, Any]:
        rows, total = self._repository.list_resources(page, page_size, enabled)
        return {
            "list": [self._resource_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    def create_resource(self, request: ApiResourceCreateRequest) -> dict[str, Any]:
        row = self._repository.create_resource(
            {
                "name": request.name,
                "description": request.description,
                "method": _method(request.method),
                "endpoint": request.endpoint,
                "auth_mode": request.auth_mode,
                "headers": request.headers,
                "body_template": request.body_template,
                "input_schema": request.input_schema,
                "output_schema": request.output_schema,
                "timeout_ms": _positive_timeout(request.timeout_ms),
                "test_payload": request.test_payload,
                "enabled": request.enabled,
            }
        )
        return self._resource_response(row)

    def get_resource(self, resource_id: int) -> dict[str, Any]:
        row = self._repository.get_resource(resource_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "API Resource not found")
        return self._resource_response(row)

    def update_resource(self, resource_id: int, request: ApiResourceUpdateRequest) -> dict[str, Any]:
        values: dict[str, Any] = {}
        if request.name is not None:
            values["name"] = request.name
        if request.description is not None:
            values["description"] = request.description
        if request.method is not None:
            values["method"] = _method(request.method)
        if request.endpoint is not None:
            values["endpoint"] = request.endpoint
        if request.auth_mode is not None:
            values["auth_mode"] = request.auth_mode
        if request.headers is not None:
            values["headers"] = request.headers
        if request.body_template is not None:
            values["body_template"] = request.body_template
        if request.input_schema is not None:
            values["input_schema"] = request.input_schema
        if request.output_schema is not None:
            values["output_schema"] = request.output_schema
        if request.timeout_ms is not None:
            values["timeout_ms"] = _positive_timeout(request.timeout_ms)
        if request.test_payload is not None:
            values["test_payload"] = request.test_payload
        if request.enabled is not None:
            values["enabled"] = request.enabled
        row = self._repository.update_resource(resource_id, values)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "API Resource not found")
        return self._resource_response(row)

    def delete_resource(self, resource_id: int) -> None:
        if not self._repository.delete_resource(resource_id):
            raise BizError(ErrorCode.NOT_FOUND, "API Resource not found")

    def test_call(self, resource_id: int, request: ApiResourceTestCallRequest) -> dict[str, Any]:
        row = self._resource_row(resource_id)
        input_values = dict(request.input or row.get("test_payload") or {})
        result = self._invoke_resource(row, input_values)
        return {
            "status": "SUCCEEDED" if result.success else "FAILED",
            "response": result.response,
            "evidence": result.evidence,
            "elapsedMs": result.elapsed_ms,
            "errorMessage": result.error_message,
        }

    def list_tools(
        self,
        page: int,
        page_size: int,
        adapter_type: str | None = None,
        model_callable: bool | None = None,
        enabled: bool | None = None,
    ) -> dict[str, Any]:
        rows, total = self._repository.list_tools(page, page_size, adapter_type, model_callable, enabled)
        return {
            "list": [self._tool_response(row) for row in rows],
            "total": total,
            "page": page,
            "pageSize": page_size,
        }

    def create_tool(self, request: ApiToolCreateRequest) -> dict[str, Any]:
        adapter_type = _adapter_type(request.adapter_type)
        if adapter_type == "API_RESOURCE" and request.api_resource_id is None:
            raise BizError(ErrorCode.BAD_REQUEST, "API-backed Tool requires apiResourceId")
        if request.api_resource_id is not None:
            self._resource_row(int(request.api_resource_id))
        row = self._repository.create_tool(
            {
                "name": request.name,
                "display_name": request.display_name,
                "description": request.description,
                "adapter_type": adapter_type,
                "api_resource_id": request.api_resource_id,
                "input_schema": request.input_schema,
                "output_schema": request.output_schema,
                "model_callable": request.model_callable,
                "enabled": request.enabled,
                "timeout_ms": _positive_timeout(request.timeout_ms),
                "retry_count": max(0, int(request.retry_count)),
                "error_behavior": request.error_behavior,
            }
        )
        return self._tool_response(row)

    def execute_api_tool(
        self,
        resource_id: str,
        tool_name: str,
        arguments: dict[str, object],
        timeout_ms: int | None = None,
    ) -> ApiResourceCallResult:
        tool = self._tool_row(resource_id, tool_name)
        if not bool(tool.get("enabled")):
            return _failed_api_result("API-backed Tool is disabled", resource_id, "API_TOOL")
        if _adapter_type(tool.get("adapter_type")) != "API_RESOURCE":
            return _failed_api_result("Unsupported API Tool adapter", resource_id, "API_TOOL")
        api_resource_id = tool.get("api_resource_id")
        if api_resource_id is None:
            return _failed_api_result("API-backed Tool has no API Resource", resource_id, "API_TOOL")
        resource = self._resource_row(int(api_resource_id))
        call_timeout = timeout_ms or int(tool.get("timeout_ms") or 30_000)
        result = self._invoke_resource(resource, arguments, timeout_ms=call_timeout)
        evidence = {
            **result.evidence,
            "resourceId": _tool_resource_id(tool),
            "resourceType": "API_TOOL",
            "toolName": str(tool.get("name") or tool_name),
            "adapter": "API_RESOURCE",
        }
        return ApiResourceCallResult(
            success=result.success,
            result=result.response.get("body"),
            elapsed_ms=result.elapsed_ms,
            error_message=result.error_message,
            response=result.response,
            evidence=evidence,
        )

    def execute_api_resource(
        self,
        resource_id: str,
        arguments: dict[str, object],
        overrides: dict[str, Any] | None = None,
        timeout_ms: int | None = None,
    ) -> ApiResourceCallResult:
        row = self._resource_row(_parse_resource_id(resource_id, "api-resource"))
        return self._invoke_resource(row, arguments, overrides=overrides, timeout_ms=timeout_ms)

    def _resource_row(self, resource_id: int) -> dict[str, Any]:
        row = self._repository.get_resource(resource_id)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "API Resource not found")
        return row

    def _tool_row(self, resource_id: str, tool_name: str) -> dict[str, Any]:
        tool_id = _parse_resource_id(resource_id, "api-tool", required=False)
        if tool_id is not None:
            row = self._repository.get_tool(tool_id)
            if row is not None:
                return row
        row = self._repository.find_tool(tool_name)
        if row is None:
            raise BizError(ErrorCode.NOT_FOUND, "API-backed Tool not found")
        return row

    def _invoke_resource(
        self,
        row: dict[str, Any],
        arguments: dict[str, object],
        overrides: dict[str, Any] | None = None,
        timeout_ms: int | None = None,
    ) -> ApiResourceCallResult:
        if not bool(row.get("enabled")):
            return _failed_api_result("API Resource is disabled", f"api-resource:{row['id']}", "API_RESOURCE")
        overrides = overrides or {}
        _validate_required(row.get("input_schema"), arguments)
        method = _method(overrides.get("method") or row.get("method") or "GET")
        endpoint = _render_template(str(overrides.get("endpoint") or overrides.get("url") or row.get("endpoint") or ""), arguments)
        if not endpoint:
            return _failed_api_result("API Resource endpoint is empty", f"api-resource:{row['id']}", "API_RESOURCE")
        headers, evidence_headers = _headers(row.get("headers"), arguments)
        override_headers, override_evidence_headers = _headers(overrides.get("headers"), arguments)
        headers.update(override_headers)
        evidence_headers.update(override_evidence_headers)
        raw_body = overrides.get("bodyTemplate")
        if raw_body is None:
            raw_body = overrides.get("body")
        if raw_body is None:
            raw_body = row.get("body_template")
        payload = _render_payload(raw_body, arguments)
        request_kwargs: dict[str, Any] = {"headers": headers}
        if payload is not None and method not in {"GET", "HEAD"}:
            if isinstance(payload, str):
                request_kwargs["content"] = payload
            else:
                request_kwargs["json"] = payload
        timeout_seconds = max(0.1, (timeout_ms or int(row.get("timeout_ms") or 30_000)) / 1000)
        started_at = perf_counter()
        status_code = 0
        response_body: Any = ""
        error_message = ""
        try:
            with httpx.Client(timeout=timeout_seconds, trust_env=False) as client:
                response = client.request(method, endpoint, **request_kwargs)
            status_code = response.status_code
            response_body = _response_payload(response)
            if response.status_code >= 400:
                error_message = f"API Resource call failed: HTTP {response.status_code}"
        except httpx.HTTPError as exc:
            error_message = f"API Resource call failed: {exc}"
        elapsed_ms = int((perf_counter() - started_at) * 1000)
        success = not error_message
        response_data = {
            "statusCode": status_code,
            "body": response_body,
        }
        evidence = {
            "resourceId": f"api-resource:{int(row['id'])}",
            "resourceType": "API_RESOURCE",
            "adapter": "API_RESOURCE",
            "method": method,
            "url": endpoint,
            "sanitizedInput": dict(arguments),
            "sanitizedRequest": {
                "headers": evidence_headers,
                "hasBody": payload is not None,
            },
            "response": {
                "statusCode": status_code,
                "bodyPreview": _body_preview(response_body),
            },
            "latencyMs": elapsed_ms,
            "timeoutMs": int(timeout_seconds * 1000),
            "status": "SUCCEEDED" if success else "FAILED",
            "errorMessage": error_message,
        }
        return ApiResourceCallResult(
            success=success,
            result=response_body,
            elapsed_ms=elapsed_ms,
            error_message=error_message,
            response=response_data,
            evidence=evidence,
        )

    def _resource_response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "name": str(row["name"]),
            "description": str(row.get("description") or ""),
            "method": str(row.get("method") or "GET"),
            "endpoint": str(row.get("endpoint") or ""),
            "authMode": str(row.get("auth_mode") or "none"),
            "headers": row.get("headers") or [],
            "bodyTemplate": str(row.get("body_template") or ""),
            "inputSchema": row.get("input_schema") or {"type": "object", "properties": {}},
            "outputSchema": row.get("output_schema") or {"type": "object", "properties": {}},
            "timeoutMs": int(row.get("timeout_ms") or 30_000),
            "testPayload": row.get("test_payload") or {},
            "enabled": bool(row.get("enabled")),
            "resourceId": f"api-resource:{int(row['id'])}",
            "createdAt": format_datetime(row["created_at"]),
            "updatedAt": format_datetime(row["updated_at"]),
        }

    def _tool_response(self, row: dict[str, Any]) -> dict[str, Any]:
        return {
            "id": int(row["id"]),
            "resourceId": _tool_resource_id(row),
            "resourceType": "API_TOOL",
            "name": str(row["name"]),
            "displayName": str(row.get("display_name") or row["name"]),
            "description": str(row.get("description") or ""),
            "adapterType": str(row.get("adapter_type") or "API_RESOURCE"),
            "apiResourceId": int(row["api_resource_id"]) if row.get("api_resource_id") is not None else None,
            "inputSchema": row.get("input_schema") or {"type": "object", "properties": {}},
            "outputSchema": row.get("output_schema") or {"type": "object", "properties": {"result": {"type": "string"}}},
            "modelCallable": bool(row.get("model_callable")),
            "enabled": bool(row.get("enabled")),
            "timeoutMs": int(row.get("timeout_ms") or 30_000),
            "retryCount": int(row.get("retry_count") or 0),
            "errorBehavior": str(row.get("error_behavior") or "fail"),
            "createdAt": format_datetime(row["created_at"]),
            "updatedAt": format_datetime(row["updated_at"]),
        }


def _tool_resource_id(row: dict[str, Any]) -> str:
    return f"api-tool:{int(row['id'])}:{row['name']}"


def _method(value: Any) -> str:
    method = str(value or "GET").strip().upper()
    return method if method in {"GET", "POST", "PUT", "PATCH", "DELETE", "HEAD"} else "GET"


def _adapter_type(value: Any) -> str:
    return str(value or "API_RESOURCE").strip().upper().replace("-", "_")


def _positive_timeout(value: Any) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return 30_000
    return parsed if parsed > 0 else 30_000


def _parse_resource_id(resource_id: str, prefix: str, required: bool = True) -> int | None:
    match = re.match(rf"^{re.escape(prefix)}:(\d+)(?::.*)?$", str(resource_id or ""))
    if match:
        return int(match.group(1))
    if str(resource_id or "").isdigit():
        return int(resource_id)
    if required:
        raise BizError(ErrorCode.BAD_REQUEST, f"Invalid {prefix} resourceId")
    return None


def _headers(raw_headers: Any, arguments: dict[str, object]) -> tuple[dict[str, str], dict[str, str]]:
    if raw_headers is None:
        return {}, {}
    if isinstance(raw_headers, str) and raw_headers.strip():
        try:
            raw_headers = json.loads(_render_template(raw_headers, arguments))
        except json.JSONDecodeError:
            return {}, {}
    headers: dict[str, str] = {}
    evidence: dict[str, str] = {}
    if isinstance(raw_headers, dict):
        items = [{"name": key, "value": value} for key, value in raw_headers.items()]
    elif isinstance(raw_headers, list):
        items = raw_headers
    else:
        items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or item.get("key") or "").strip()
        if not name:
            continue
        value = _render_template(str(item.get("value") or ""), arguments)
        headers[name] = value
        evidence[name] = "***" if _sensitive_header(name, item) else value
    return headers, evidence


def _sensitive_header(name: str, item: dict[str, Any]) -> bool:
    if item.get("sensitive") is True:
        return True
    lowered = name.lower()
    return any(token in lowered for token in ("authorization", "token", "secret", "key", "password"))


def _render_payload(value: Any, arguments: dict[str, object]) -> Any:
    if value is None or value == "":
        return None
    if isinstance(value, str):
        rendered = _render_template(value, arguments)
        try:
            return json.loads(rendered)
        except json.JSONDecodeError:
            return rendered
    if isinstance(value, dict):
        return {str(key): _render_payload(item, arguments) for key, item in value.items()}
    if isinstance(value, list):
        return [_render_payload(item, arguments) for item in value]
    return value


def _render_template(template: str, arguments: dict[str, object]) -> str:
    pattern = re.compile(r"\{\{\s*([A-Za-z0-9_.-]+)\s*\}\}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        if key in arguments:
            value = arguments[key]
        elif "." in key:
            value = arguments.get(key.split(".")[-1])
        else:
            value = None
        return "" if value is None else str(value)

    return pattern.sub(replace, template)


def _response_payload(response: httpx.Response) -> Any:
    content_type = response.headers.get("Content-Type", "")
    if "json" in content_type.lower():
        return response.json()
    try:
        return response.json()
    except ValueError:
        return response.text


def _validate_required(schema: Any, arguments: dict[str, object]) -> None:
    if not isinstance(schema, dict):
        return
    required = schema.get("required")
    if not isinstance(required, list):
        return
    missing = [str(name) for name in required if not _not_empty(arguments.get(str(name)))]
    if missing:
        raise BizError(ErrorCode.BAD_REQUEST, f"Missing API Resource input: {', '.join(missing)}")


def _not_empty(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    return True


def _body_preview(value: Any) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text[:500]


def _failed_api_result(message: str, resource_id: str, resource_type: str) -> ApiResourceCallResult:
    evidence = {
        "resourceId": resource_id,
        "resourceType": resource_type,
        "adapter": "API_RESOURCE",
        "status": "FAILED",
        "errorMessage": message,
        "latencyMs": 0,
    }
    return ApiResourceCallResult(
        success=False,
        result=None,
        elapsed_ms=0,
        error_message=message,
        response={"statusCode": 0, "body": ""},
        evidence=evidence,
    )
