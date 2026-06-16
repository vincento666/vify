from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class MockActionExecutionResult:
    executor_ref: str
    status: str
    audit_payload: dict[str, Any]
    error: dict[str, Any] | None = None


class MockActionExecutorRegistry:
    def execute(self, action_type: str, payload: dict[str, Any]) -> MockActionExecutionResult:
        if action_type == "submit_refund":
            order_no = str(payload.get("orderNo") or payload.get("order_no") or "UNKNOWN")
            return MockActionExecutionResult(
                executor_ref="refund_submit_mock",
                status="EXECUTED",
                audit_payload={
                    "executionKey": f"refund_submit_mock:{order_no}",
                    "orderNo": order_no,
                    "semanticCode": "REFUND_SUBMITTED_MOCK",
                    "executedAt": datetime.now().isoformat(),
                    "sideEffects": [],
                },
            )
        return MockActionExecutionResult(
            executor_ref="unsupported_action_mock",
            status="FAILED",
            audit_payload={
                "executionKey": f"unsupported_action_mock:{action_type}",
                "semanticCode": "UNSUPPORTED_ACTION",
                "executedAt": datetime.now().isoformat(),
                "sideEffects": [],
            },
            error={"code": "UNSUPPORTED_ACTION", "message": f"No mock executor for {action_type}"},
        )
