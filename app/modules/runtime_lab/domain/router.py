from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from app.modules.runtime_lab.domain.sop import MockSopAdapter, SopManifest, mock_sop_manifests


@dataclass(frozen=True)
class RouteDecision:
    action: str
    reason: str
    target_sop_id: str | None = None
    active_task_id: int | None = None
    matched_keyword: str | None = None


class RuntimeLabRouter:
    def __init__(self, adapter: MockSopAdapter | None = None, manifests: dict[str, SopManifest] | None = None) -> None:
        self._manifests = manifests or mock_sop_manifests()
        self._adapter = adapter or MockSopAdapter(self._manifests)

    def decide(
        self,
        message: str,
        active_task: Mapping[str, Any] | None = None,
        suspended_tasks: Sequence[Mapping[str, Any]] | None = None,
    ) -> RouteDecision:
        suspended = suspended_tasks or ()
        suspended_count = len(suspended)
        if active_task is None and suspended_count == 1 and _is_resume_phrase(message):
            return RouteDecision(
                action="RESUME_TASK",
                active_task_id=_task_id(suspended[0]),
                reason="Resume phrase resolved to single suspended task",
            )
        matched = self._match_strong_keyword(message)
        active_task_id = _task_id(active_task)
        if active_task is None and matched is not None:
            return RouteDecision(
                action="START_SOP",
                target_sop_id=matched.sop_id,
                matched_keyword=matched.keyword,
                reason=f"Matched strong keyword: {matched.keyword}",
            )
        if active_task is not None and matched is not None:
            active_sop_id = str(active_task.get("sop_id") or "")
            if matched.sop_id != active_sop_id:
                if suspended_count >= 1:
                    return RouteDecision(
                        action="REJECT_SWITCH_SUSPENDED_LIMIT",
                        target_sop_id=matched.sop_id,
                        active_task_id=active_task_id,
                        matched_keyword=matched.keyword,
                        reason="029 policy allows at most one suspended task",
                    )
                current_step = str(active_task.get("current_step") or "")
                if self._adapter.is_interruptible(active_sop_id, current_step):
                    return RouteDecision(
                        action="SUSPEND_AND_START",
                        target_sop_id=matched.sop_id,
                        active_task_id=active_task_id,
                        matched_keyword=matched.keyword,
                        reason=f"Strong keyword switch at interruptible step: {matched.keyword}",
                    )
                return RouteDecision(
                    action="REJECT_SWITCH_CONTINUE_ACTIVE",
                    target_sop_id=matched.sop_id,
                    active_task_id=active_task_id,
                    matched_keyword=matched.keyword,
                    reason="Active task current step is not interruptible",
                )
            return RouteDecision(
                action="CONTINUE_ACTIVE_SOP",
                active_task_id=active_task_id,
                matched_keyword=matched.keyword,
                reason="Matched active SOP keyword or non-switch context",
            )
        if active_task is not None:
            return RouteDecision(
                action="CONTINUE_ACTIVE_SOP",
                active_task_id=active_task_id,
                reason="Active task exists and no strong switch matched",
            )
        return RouteDecision(action="NO_MATCH", reason="No strong SOP keyword matched")

    def _match_strong_keyword(self, message: str) -> "_StrongMatch | None":
        for manifest in self._manifests.values():
            for keyword in manifest.strong_trigger_keywords:
                if keyword and keyword in message:
                    return _StrongMatch(manifest.sop_id, keyword)
        return None


@dataclass(frozen=True)
class _StrongMatch:
    sop_id: str
    keyword: str


def _task_id(active_task: Mapping[str, Any] | None) -> int | None:
    if active_task is None:
        return None
    raw = active_task.get("id")
    if raw is None:
        return None
    return int(raw)


def _is_resume_phrase(message: str) -> bool:
    return message.strip().lower() in {"continue", "继续", "继续刚才", "继续第一个"}
