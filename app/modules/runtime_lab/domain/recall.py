from collections.abc import Mapping, Sequence
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown, select_top_candidates
from app.modules.runtime_lab.domain.sop import SopManifest

SEMANTIC_FIXTURES: dict[str, tuple[str, ...]] = {
    "refund_ticket": ("退费", "票款", "取消行程", "退掉航班"),
    "change_flight": ("换个航班", "改时间", "调整航班", "改日期"),
    "invoice_apply": ("报销", "凭证", "电子票据", "开票资料", "发票"),
}


class MockSemanticCandidateRecall:
    def __init__(self, manifests: dict[str, SopManifest]) -> None:
        self._manifests = manifests

    def recall(
        self,
        message: str,
        active_task: Mapping[str, Any] | None,
        suspended_tasks: Sequence[Mapping[str, Any]],
        top_k: int = 5,
    ) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        if active_task is not None:
            candidates.append(self._active_candidate(active_task))
        candidates.extend(self._suspended_candidates(message, suspended_tasks))
        candidates.extend(self._sop_candidates(message))
        return select_top_candidates(candidates, top_k)

    def _active_candidate(self, active_task: Mapping[str, Any]) -> RouteCandidate:
        task_id = str(active_task["id"])
        sop_id = str(active_task.get("sop_id") or "")
        return RouteCandidate(
            candidate_id=f"active:{task_id}",
            candidate_type=CandidateType.ACTIVE_TASK_CONTINUE,
            target_id=task_id,
            display_name=f"Continue {sop_id}",
            source="mock_semantic_recall",
            score=0.55,
            score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=0.55),
            matched_terms=(),
            risk_level="LOW",
            requires_classifier=True,
            reason="Active task continuation is always a finite candidate in active context",
        )

    def _suspended_candidates(
        self,
        message: str,
        suspended_tasks: Sequence[Mapping[str, Any]],
    ) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        for task in suspended_tasks:
            summary = str(task.get("resume_summary") or "")
            sop_id = str(task.get("sop_id") or "")
            terms = tuple(term for term in (summary, sop_id, "退票", "改签", "发票") if term and term in message)
            if not terms:
                continue
            score = 0.92 if "继续" in message or "resume" in message.lower() else 0.72
            task_id = str(task["id"])
            candidates.append(
                RouteCandidate(
                    candidate_id=f"suspended:{task_id}",
                    candidate_type=CandidateType.SUSPENDED_TASK_RESUME,
                    target_id=task_id,
                    display_name=f"Resume {sop_id}",
                    source="mock_semantic_recall",
                    score=score,
                    score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
                    matched_terms=terms,
                    risk_level="LOW",
                    requires_classifier=True,
                    reason="Message overlaps suspended task resume summary",
                )
            )
        return candidates

    def _sop_candidates(self, message: str) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        for sop_id, manifest in self._manifests.items():
            matched = tuple(term for term in SEMANTIC_FIXTURES.get(sop_id, ()) if term in message)
            if not matched:
                continue
            score = 0.78
            candidates.append(
                RouteCandidate(
                    candidate_id=f"sop:{sop_id}",
                    candidate_type=CandidateType.SOP_INTENT,
                    target_id=sop_id,
                    display_name=manifest.display_name,
                    source="mock_semantic_recall",
                    score=score,
                    score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=score),
                    matched_terms=matched,
                    risk_level="LOW",
                    requires_classifier=True,
                    reason="Mock semantic fixture matched SOP intent",
                )
            )
        return candidates
