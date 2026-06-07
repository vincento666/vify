from dataclasses import dataclass
from typing import Any

from app.modules.runtime_lab.domain.router import RouteDecision, RuntimeLabRouter
from app.modules.runtime_lab.domain.sop import MockSopAdapter, SopTurnResult
from app.modules.runtime_lab.infra.repository import RuntimeLabRepository


@dataclass(frozen=True)
class RuntimeLabTurn:
    reply: str
    route_decision: RouteDecision
    active_task: dict[str, Any] | None
    suspended_tasks: list[dict[str, Any]]
    resume_offer: dict[str, Any] | None
    events: list[dict[str, Any]]


class RuntimeLabService:
    def __init__(
        self,
        repository: RuntimeLabRepository,
        router: RuntimeLabRouter | None = None,
        adapter: MockSopAdapter | None = None,
    ) -> None:
        self._repository = repository
        self._adapter = adapter or MockSopAdapter()
        self._router = router or RuntimeLabRouter(self._adapter)

    def create_session(self) -> dict[str, Any]:
        runtime_session = self._repository.create_session()
        self._repository.append_event(int(runtime_session["id"]), "SESSION_CREATED", {})
        return runtime_session

    def handle_message(self, session_id: int, message: str) -> RuntimeLabTurn:
        self._repository.append_event(session_id, "USER_MESSAGE", {"message": message})
        active_task = self._repository.get_active_task(session_id)
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        decision = self._router.decide(message, active_task=active_task, suspended_tasks=suspended_tasks)
        self._repository.append_event(session_id, "ROUTE_DECISION", _decision_payload(decision))

        if decision.action == "START_SOP" and decision.target_sop_id is not None:
            result = self._adapter.start(decision.target_sop_id)
            task = self._start_task(session_id, result)
            self._repository.append_event(
                session_id,
                "TASK_STARTED",
                {"taskId": task["id"], "sopId": task["sop_id"]},
            )
            return self._turn(session_id, result.reply, decision)

        if decision.action == "SUSPEND_AND_START" and active_task is not None and decision.target_sop_id is not None:
            suspended = self._suspend_task(session_id, active_task)
            self._repository.append_event(
                session_id,
                "TASK_SUSPENDED",
                {"taskId": suspended["id"], "sopId": suspended["sop_id"]},
            )
            result = self._adapter.start(decision.target_sop_id)
            task = self._start_task(session_id, result)
            self._repository.append_event(
                session_id,
                "TASK_STARTED",
                {"taskId": task["id"], "sopId": task["sop_id"]},
            )
            return self._turn(session_id, result.reply, decision)

        if decision.action in {"REJECT_SWITCH_CONTINUE_ACTIVE", "REJECT_SWITCH_SUSPENDED_LIMIT"}:
            self._repository.append_event(session_id, "SWITCH_REJECTED", _decision_payload(decision))
            if decision.action == "REJECT_SWITCH_SUSPENDED_LIMIT":
                return self._turn(session_id, "当前已有一个暂停流程，请先完成或恢复后再切换。", decision)
            return self._turn(session_id, "当前步骤不能中断，请先完成确认后再切换。", decision)

        if decision.action == "RESUME_TASK":
            return self._resume_task(session_id, decision)

        if decision.action == "CONTINUE_ACTIVE_SOP" and active_task is not None:
            return self._continue_active_task(session_id, active_task, message, decision)

        return self._turn(session_id, "暂未匹配到可执行的航空业务流程。", decision)

    def _start_task(self, session_id: int, result: SopTurnResult) -> dict[str, Any]:
        task = self._repository.create_task(
            session_id,
            sop_id=result.sop_id,
            current_step=result.current_step,
            business_refs=result.collected,
        )
        checkpoint = self._repository.create_checkpoint(
            session_id,
            int(task["id"]),
            sop_id=result.sop_id,
            current_step=result.current_step,
            pending_prompt=result.pending_prompt,
            collected=result.collected,
            status=result.checkpoint["status"],
        )
        return self._repository.update_task_state(
            int(task["id"]),
            status="RUNNING",
            current_step=result.current_step,
            checkpoint_id=int(checkpoint["id"]),
            business_refs=result.collected,
        )

    def _suspend_task(self, session_id: int, task: dict[str, Any]) -> dict[str, Any]:
        checkpoint = self._repository.get_latest_checkpoint(int(task["id"]))
        collected = dict(checkpoint["collected"]) if checkpoint else dict(task.get("business_refs") or {})
        pending_prompt = str(checkpoint["pending_prompt"]) if checkpoint else ""
        checkpoint = self._repository.create_checkpoint(
            session_id,
            int(task["id"]),
            sop_id=str(task["sop_id"]),
            current_step=str(task["current_step"]),
            pending_prompt=pending_prompt,
            collected=collected,
        )
        summary = f"{task['sop_id']} paused at {task['current_step']}"
        return self._repository.update_task_state(
            int(task["id"]),
            status="SUSPENDED",
            checkpoint_id=int(checkpoint["id"]),
            resume_summary=summary,
            business_refs=collected,
        )

    def _continue_active_task(
        self,
        session_id: int,
        active_task: dict[str, Any],
        message: str,
        decision: RouteDecision,
    ) -> RuntimeLabTurn:
        checkpoint = self._repository.get_latest_checkpoint(int(active_task["id"]))
        collected = dict(checkpoint["collected"]) if checkpoint else dict(active_task.get("business_refs") or {})
        result = self._adapter.continue_task(
            sop_id=str(active_task["sop_id"]),
            current_step=str(active_task["current_step"]),
            message=message,
            collected=collected,
        )
        saved_checkpoint = self._repository.create_checkpoint(
            session_id,
            int(active_task["id"]),
            sop_id=result.sop_id,
            current_step=result.current_step,
            pending_prompt=result.pending_prompt,
            collected=result.collected,
            status=result.checkpoint["status"],
        )
        if result.completed:
            completed = self._repository.update_task_state(
                int(active_task["id"]),
                status="COMPLETED",
                current_step=result.current_step,
                checkpoint_id=int(saved_checkpoint["id"]),
                business_refs=result.collected,
            )
            complete_decision = RouteDecision(
                action="COMPLETE_TASK",
                reason="Active SOP completed after confirmation",
                active_task_id=int(completed["id"]),
            )
            self._repository.append_event(
                session_id,
                "TASK_COMPLETED",
                {"taskId": completed["id"], "sopId": completed["sop_id"]},
            )
            resume_offer = self._build_resume_offer(session_id)
            if resume_offer is not None:
                self._repository.append_event(session_id, "RESUME_OFFERED", resume_offer)
            return self._turn(session_id, result.reply, complete_decision, resume_offer=resume_offer)

        task = self._repository.update_task_state(
            int(active_task["id"]),
            status="RUNNING",
            current_step=result.current_step,
            checkpoint_id=int(saved_checkpoint["id"]),
            business_refs=result.collected,
        )
        self._repository.append_event(
            session_id,
            "TASK_CONTINUED",
            {"taskId": task["id"], "sopId": task["sop_id"], "currentStep": task["current_step"]},
        )
        return self._turn(session_id, result.reply, decision)

    def _resume_task(self, session_id: int, decision: RouteDecision) -> RuntimeLabTurn:
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        if not suspended_tasks:
            return self._turn(session_id, "没有可恢复的暂停流程。", RouteDecision(action="NO_MATCH", reason="No suspended task"))
        task = suspended_tasks[0]
        checkpoint = self._repository.get_latest_checkpoint(int(task["id"]))
        collected = dict(checkpoint["collected"]) if checkpoint else dict(task.get("business_refs") or {})
        current_step = str(checkpoint["current_step"]) if checkpoint else str(task["current_step"])
        checkpoint_id = int(checkpoint["id"]) if checkpoint else int(task["checkpoint_id"] or 0)
        resumed = self._repository.update_task_state(
            int(task["id"]),
            status="RUNNING",
            current_step=current_step,
            checkpoint_id=checkpoint_id,
            business_refs=collected,
        )
        self._repository.append_event(
            session_id,
            "TASK_RESUMED",
            {"taskId": resumed["id"], "sopId": resumed["sop_id"], "currentStep": resumed["current_step"]},
        )
        prompt = str(checkpoint["pending_prompt"]) if checkpoint else "请继续提供信息。"
        return self._turn(session_id, f"已恢复刚才的流程。{prompt}", decision)

    def _build_resume_offer(self, session_id: int) -> dict[str, Any] | None:
        suspended_tasks = self._repository.list_tasks(session_id, statuses={"SUSPENDED"})
        if not suspended_tasks:
            return None
        task = suspended_tasks[0]
        return {
            "taskId": task["id"],
            "sopId": task["sop_id"],
            "resumeSummary": task["resume_summary"],
            "prompt": "是否继续刚才中断的流程？",
        }

    def _turn(
        self,
        session_id: int,
        reply: str,
        decision: RouteDecision,
        resume_offer: dict[str, Any] | None = None,
    ) -> RuntimeLabTurn:
        return RuntimeLabTurn(
            reply=reply,
            route_decision=decision,
            active_task=self._repository.get_active_task(session_id),
            suspended_tasks=self._repository.list_tasks(session_id, statuses={"SUSPENDED"}),
            resume_offer=resume_offer,
            events=self._repository.list_events(session_id),
        )


def _decision_payload(decision: RouteDecision) -> dict[str, Any]:
    return {
        "action": decision.action,
        "reason": decision.reason,
        "targetSopId": decision.target_sop_id,
        "activeTaskId": decision.active_task_id,
        "matchedKeyword": decision.matched_keyword,
    }
