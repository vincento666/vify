from __future__ import annotations

from typing import Any


def build_activity_correlation_ids(
    *,
    run_id: int,
    event_type: str,
    payload: dict[str, Any] | None = None,
    task_id: int | None = None,
    tool_call_id: int | None = None,
    provided: dict[str, Any] | None = None,
) -> dict[str, Any]:
    correlation = dict(provided or {})
    if correlation.get("activityId"):
        return correlation
    body = dict(payload or {})
    normalized_type = str(event_type or "").strip().lower()
    activity_id = ""
    activity_kind = ""

    if normalized_type.startswith("approval."):
        approval_id = _value(body.get("approvalId"))
        if approval_id:
            activity_id = f"approval:{approval_id}"
            activity_kind = "approval"
    elif normalized_type.startswith("subagent.execution_"):
        execution_id = _value(body.get("executionId") or body.get("subAgentRunId"))
        if execution_id:
            activity_id = f"subagent:{execution_id}"
            activity_kind = "subagent"
    elif normalized_type.startswith("plan.step_"):
        step = body.get("step")
        step_body = step if isinstance(step, dict) else {}
        step_id = _value(step_body.get("id") or body.get("stepId"))
        if step_id:
            activity_id = f"run:{run_id}:step:{step_id}"
            activity_kind = "step"
    elif normalized_type.startswith("tool.") and tool_call_id is not None:
        tool_name = _value(body.get("toolName"))
        activity_kind = _tool_kind(tool_name)
        activity_id = f"{activity_kind}:{run_id}:call:{tool_call_id}"
    elif normalized_type.startswith("task."):
        phase = _value(body.get("phase"))
        identity = _value(task_id) or phase or normalized_type
        activity_id = f"run:{run_id}:phase:{identity}"
        activity_kind = "phase"
    elif normalized_type.startswith("run.") or normalized_type.startswith("orchestration.phase_"):
        phase = _value(body.get("phase")) or normalized_type.removeprefix("run.")
        activity_id = f"run:{run_id}:phase:{phase}"
        activity_kind = "phase"

    if activity_id:
        correlation["activityId"] = activity_id
        correlation["activityKind"] = activity_kind
    return correlation


def tool_activity_correlation_ids(
    *,
    run_id: int,
    tool_name: str,
    step: dict[str, Any] | None = None,
    scheduler: dict[str, Any] | None = None,
) -> dict[str, Any]:
    step_id = _value((step or {}).get("id"))
    scheduler_identity = ""
    if scheduler:
        batch_id = _value(scheduler.get("schedulerBatchId"))
        position = _value(scheduler.get("schedulerPosition"))
        if batch_id and position:
            scheduler_identity = f"batch:{batch_id}:position:{position}"
    identity = step_id or scheduler_identity or tool_name
    kind = _tool_kind(tool_name)
    correlation: dict[str, Any] = {
        "activityId": f"{kind}:{run_id}:{identity}",
        "activityKind": kind,
        "toolName": tool_name,
    }
    if step_id:
        correlation["planStepId"] = step_id
        correlation["parentActivityId"] = f"run:{run_id}:step:{step_id}"
    if scheduler:
        correlation["scheduler"] = scheduler
    return correlation


def _tool_kind(tool_name: str) -> str:
    if tool_name in {"invoke_skill", "read_skill_resource", "run_skill_script"}:
        return "skill"
    return "tool"


def _value(value: object) -> str:
    if value is None:
        return ""
    return str(value).strip()


__all__ = [
    "build_activity_correlation_ids",
    "tool_activity_correlation_ids",
]
