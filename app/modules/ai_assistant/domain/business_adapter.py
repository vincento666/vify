from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

from app.modules.ai_assistant.domain.tools import RiskLevel, ToolManifest, ToolResult


@dataclass(frozen=True)
class BusinessToolSchema:
    adapter_name: str
    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    risk_level: str
    idempotency_fields: list[str]
    compensation: dict[str, Any]
    audit_fields: list[str]


@dataclass(frozen=True)
class BusinessToolResult:
    tool_name: str
    status: str
    output: dict[str, Any]
    idempotency_key: str
    compensation_transaction: dict[str, Any]
    audit: dict[str, Any]


class BusinessToolAdapter(Protocol):
    adapter_name: str

    def list_tool_schemas(self) -> list[BusinessToolSchema]:
        ...

    def invoke(self, tool_name: str, payload: dict[str, Any]) -> BusinessToolResult:
        ...


class MockAviationAdapter:
    adapter_name = "mock_aviation"

    def list_tool_schemas(self) -> list[BusinessToolSchema]:
        return [
            _schema("refund", risk_level="BUSINESS_WRITE", compensation_action="mock_refund_compensation"),
            _schema("change_ticket", risk_level="BUSINESS_WRITE", compensation_action="mock_change_ticket_compensation"),
            _schema("baggage", risk_level="READ", compensation_action="mock_baggage_noop_compensation"),
            _schema(
                "flight_disruption",
                risk_level="READ",
                compensation_action="mock_flight_disruption_noop_compensation",
            ),
        ]

    def invoke(self, tool_name: str, payload: dict[str, Any]) -> BusinessToolResult:
        schema = self._schema_by_name(tool_name)
        scenario = tool_name.removeprefix(f"{self.adapter_name}.")
        case_id = str(payload.get("caseId") or payload.get("case_id") or "mock-case")
        idempotency_key = f"{tool_name}:{case_id}"
        compensation = {
            "id": f"comp-{scenario}-{case_id}",
            "toolName": tool_name,
            "status": "MOCK_COMPENSATION_READY",
            "action": schema.compensation["action"],
            "mockOnly": True,
        }
        audit = {
            "adapterName": self.adapter_name,
            "toolName": tool_name,
            "scenario": scenario,
            "caseId": case_id,
            "riskLevel": schema.risk_level,
            "mockOnly": True,
            "realAviationRulesApplied": False,
            "idempotencyKey": idempotency_key,
        }
        output = {
            "status": "MOCK_ACCEPTED",
            "scenario": scenario,
            "caseId": case_id,
            "businessEffect": "mock_only",
            "message": f"Mock aviation adapter accepted {scenario}.",
            "compensationTransaction": compensation,
            "audit": audit,
        }
        return BusinessToolResult(
            tool_name=tool_name,
            status="MOCK_ACCEPTED",
            output=output,
            idempotency_key=idempotency_key,
            compensation_transaction=compensation,
            audit=audit,
        )

    def _schema_by_name(self, tool_name: str) -> BusinessToolSchema:
        for schema in self.list_tool_schemas():
            if schema.name == tool_name:
                return schema
        raise KeyError(f"Unknown mock aviation tool: {tool_name}")


def mock_aviation_eval_cases() -> list[dict[str, Any]]:
    return [
        {
            "scenario": "refund",
            "toolName": "mock_aviation.refund",
            "input": {"caseId": "eval-refund", "passengerId": "PAX-001", "request": "refund"},
        },
        {
            "scenario": "change_ticket",
            "toolName": "mock_aviation.change_ticket",
            "input": {"caseId": "eval-change", "passengerId": "PAX-002", "request": "change ticket"},
        },
        {
            "scenario": "baggage",
            "toolName": "mock_aviation.baggage",
            "input": {"caseId": "eval-baggage", "passengerId": "PAX-003", "request": "baggage"},
        },
        {
            "scenario": "flight_disruption",
            "toolName": "mock_aviation.flight_disruption",
            "input": {"caseId": "eval-disruption", "passengerId": "PAX-004", "request": "flight disruption"},
        },
    ]


def tool_entries_for_business_adapter(
    adapter: BusinessToolAdapter,
) -> dict[str, tuple[ToolManifest, Any]]:
    entries: dict[str, tuple[ToolManifest, Any]] = {}
    for schema in adapter.list_tool_schemas():
        manifest = ToolManifest(
            name=schema.name,
            description=schema.description,
            input_schema=schema.input_schema,
            output_schema=schema.output_schema,
            timeout_ms=1000,
            risk_level=RiskLevel(schema.risk_level),
            read_resources=[f"business_adapter:{schema.adapter_name}:{schema.name}:read"],
            write_resources=[]
            if schema.risk_level == RiskLevel.READ.value
            else [f"business_adapter:{schema.adapter_name}:{schema.name}:write"],
            policy_ref=f"business_adapter:{schema.adapter_name}:{schema.risk_level.lower()}",
        )

        def handler(payload: dict[str, Any], *, tool_name: str = schema.name) -> ToolResult:
            result = adapter.invoke(tool_name, payload)
            return ToolResult(
                status="COMPLETED",
                output={
                    **result.output,
                    "idempotencyKey": result.idempotency_key,
                    "compensationTransaction": result.compensation_transaction,
                    "audit": result.audit,
                },
            )

        entries[schema.name] = (manifest, handler)
    return entries


def _schema(scenario: str, *, risk_level: str, compensation_action: str) -> BusinessToolSchema:
    tool_name = f"mock_aviation.{scenario}"
    return BusinessToolSchema(
        adapter_name="mock_aviation",
        name=tool_name,
        description=f"Mock aviation {scenario} business-shaped tool. No real aviation rules.",
        input_schema={
            "type": "object",
            "properties": {
                "caseId": {"type": "string"},
                "passengerId": {"type": "string"},
                "request": {"type": "string"},
            },
            "required": ["caseId"],
        },
        output_schema={
            "type": "object",
            "properties": {
                "status": {"type": "string"},
                "businessEffect": {"type": "string"},
                "compensationTransaction": {"type": "object"},
                "audit": {"type": "object"},
            },
            "required": ["status", "businessEffect", "audit"],
        },
        risk_level=risk_level,
        idempotency_fields=["toolName", "caseId"],
        compensation={"action": compensation_action, "mockOnly": True},
        audit_fields=[
            "adapterName",
            "toolName",
            "scenario",
            "caseId",
            "riskLevel",
            "mockOnly",
            "realAviationRulesApplied",
            "idempotencyKey",
        ],
    )
