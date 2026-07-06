from __future__ import annotations

from enum import StrEnum
from typing import Any, cast


class PlanningStrategy(StrEnum):
    AUTO_LIGHTWEIGHT = "auto_lightweight"
    DELIBERATE = "deliberate"
    PLAN_ONLY = "plan_only"


def normalize_planning_strategy(value: str | None) -> PlanningStrategy:
    normalized = (value or PlanningStrategy.AUTO_LIGHTWEIGHT.value).strip().lower()
    for strategy in PlanningStrategy:
        if normalized == strategy.value:
            return strategy
    return PlanningStrategy.AUTO_LIGHTWEIGHT


def create_initial_plan_state(
    *,
    run_id: int,
    message: str,
    requested_strategy: str | None,
    planned_tool_names: list[str],
) -> dict[str, Any]:
    strategy = normalize_planning_strategy(requested_strategy)
    steps = [
        {
            "id": f"plan-{run_id}-step-{index}",
            "title": _step_title(tool_name),
            "status": "PENDING",
            "toolName": tool_name,
            "sequence": index,
        }
        for index, tool_name in enumerate(planned_tool_names, start=1)
    ]
    if not steps:
        steps.append(
            {
                "id": f"plan-{run_id}-step-1",
                "title": "生成回复",
                "status": "PENDING",
                "toolName": None,
                "sequence": 1,
            }
        )
    return {
        "id": f"plan-{run_id}",
        "planningStrategy": strategy.value,
        "status": "ACTIVE",
        "recognizedNeeds": [_recognized_need(message)],
        "steps": steps,
        "currentStep": steps[0],
        "plannedTools": [tool_name for tool_name in planned_tool_names if tool_name],
        "finalResult": "",
    }


def mark_plan_step_started(plan: dict[str, Any], tool_name: str | None) -> dict[str, Any]:
    updated = _copy_plan(plan)
    step = _matching_step(updated, tool_name, statuses={"PENDING", "WAITING", "BLOCKED"})
    if step is None:
        return updated
    step["status"] = "RUNNING"
    updated["status"] = "RUNNING"
    updated.pop("blockedReason", None)
    updated["currentStep"] = step
    return updated


def mark_plan_step_completed(plan: dict[str, Any], tool_name: str | None, final_result: str = "") -> dict[str, Any]:
    updated = _copy_plan(plan)
    step = _matching_step(updated, tool_name, statuses={"RUNNING", "PENDING", "WAITING"})
    if step is None:
        if final_result:
            updated["finalResult"] = final_result
        return updated
    step["status"] = "COMPLETED"
    updated["currentStep"] = step
    if final_result:
        updated["finalResult"] = final_result
    if all(step.get("status") == "COMPLETED" for step in updated.get("steps", [])):
        updated["status"] = "COMPLETED"
    return updated


def mark_plan_blocked(plan: dict[str, Any], reason: str) -> dict[str, Any]:
    updated = _copy_plan(plan)
    updated["status"] = "BLOCKED"
    updated["blockedReason"] = reason
    current = updated.get("currentStep")
    if isinstance(current, dict):
        current["status"] = "BLOCKED"
        current_id = current.get("id")
        for step in updated.get("steps") or []:
            if step.get("id") == current_id:
                step["status"] = "BLOCKED"
                updated["currentStep"] = step
                break
    return updated


def set_plan_final_result(plan: dict[str, Any], final_result: str) -> dict[str, Any]:
    updated = _copy_plan(plan)
    updated["finalResult"] = final_result
    if updated.get("steps") and all(step.get("status") == "COMPLETED" for step in updated.get("steps") or []):
        updated["status"] = "COMPLETED"
        updated.pop("blockedReason", None)
    return updated


def complete_plan_without_execution(plan: dict[str, Any], final_result: str) -> dict[str, Any]:
    updated = _copy_plan(plan)
    for step in updated.get("steps") or []:
        step["status"] = "COMPLETED"
    if updated.get("steps"):
        updated["currentStep"] = updated["steps"][-1]
    updated["finalResult"] = final_result
    updated["status"] = "COMPLETED"
    updated.pop("blockedReason", None)
    return updated


def _copy_plan(plan: dict[str, Any]) -> dict[str, Any]:
    steps = [dict(step) for step in plan.get("steps") or [] if isinstance(step, dict)]
    return {
        **plan,
        "recognizedNeeds": list(plan.get("recognizedNeeds") or []),
        "steps": steps,
        "currentStep": dict(plan.get("currentStep") or {}) if isinstance(plan.get("currentStep"), dict) else None,
    }


def _matching_step(plan: dict[str, Any], tool_name: str | None, *, statuses: set[str]) -> dict[str, Any] | None:
    steps = [cast(dict[str, Any], step) for step in plan.get("steps") or [] if isinstance(step, dict)]
    for step in steps:
        if step.get("status") in statuses and step.get("toolName") == tool_name:
            return step
    for step in steps:
        if step.get("status") in statuses:
            return step
    return None


def _recognized_need(message: str) -> str:
    stripped = " ".join(message.strip().split())
    return stripped or "处理用户请求"


def _step_title(tool_name: str) -> str:
    labels = {
        "echo_context": "回显上下文",
        "read_workspace_file": "读取工作区文件",
        "list_workspace_files": "列出工作区文件",
        "search_workspace_files": "搜索工作区文件",
        "edit_workspace_file": "编辑工作区文件",
        "write_workspace_file": "写入工作区文件",
        "apply_workspace_patch": "应用工作区补丁",
        "run_shell": "执行命令",
        "invoke_skill": "调用技能",
        "search_knowledge_base": "检索知识库",
        "update_customer_profile": "更新客户资料",
    }
    return labels.get(tool_name, tool_name)
