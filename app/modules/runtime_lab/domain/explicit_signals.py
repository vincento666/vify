from collections.abc import Mapping, Sequence, Set as AbstractSet
from typing import Any

from app.modules.runtime_lab.domain.candidates import CandidateType, RouteCandidate, ScoreBreakdown, select_top_candidates
from app.modules.runtime_lab.domain.sop import SopManifest, match_strong_trigger_template

RESUME_PHRASES = {"continue", "resume", "继续", "继续刚才", "继续第一个"}
REFUSAL_PHRASES = {"不用了", "不用", "不了", "先这样"}
HANDOFF_TRIGGER_GROUPS: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("USER_REQUEST", ("转人工", "人工客服", "找人工", "人工处理")),
    ("COMPLAINT", ("投诉", "主管", "升级处理", "不满意")),
    ("COMPLIANCE", ("监管", "民航局")),
    ("SAFETY", ("报警", "安全事故")),
    ("UNSUPPORTED", ("这个机器人处理不了", "无法办理", "不要机器人")),
)


class ExplicitSignalDetector:
    def __init__(self, manifests: dict[str, SopManifest]) -> None:
        self._manifests = manifests

    def detect(
        self,
        message: str,
        active_task: Mapping[str, Any] | None,
        suspended_tasks: Sequence[Mapping[str, Any]],
        enabled_sop_ids: AbstractSet[str] | None = None,
        top_k: int = 5,
    ) -> list[RouteCandidate]:
        text = message.strip()
        candidates: list[RouteCandidate] = []
        handoff = self._handoff_candidate(text)
        if handoff is not None:
            candidates.append(handoff)
        refusal = self._refusal_candidate(text)
        if refusal is not None:
            candidates.append(refusal)
        candidates.extend(self._resume_candidates(text, suspended_tasks))
        candidates.extend(self._sop_candidates(text, active_task, enabled_sop_ids))
        return select_top_candidates(candidates, top_k)

    def _handoff_candidate(self, text: str) -> RouteCandidate | None:
        for reason_code, terms in HANDOFF_TRIGGER_GROUPS:
            matched_terms = tuple(term for term in terms if term in text)
            if not matched_terms:
                continue
            return RouteCandidate(
                candidate_id=f"handoff:{reason_code}",
                candidate_type=CandidateType.HANDOFF_TO_HUMAN,
                target_id=reason_code,
                display_name="Human handoff",
                source="explicit_signal",
                score=1.0,
                score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
                matched_terms=matched_terms,
                risk_level="HIGH",
                requires_classifier=False,
                reason=f"Explicit handoff trigger: {reason_code}",
            )
        return None

    def _refusal_candidate(self, text: str) -> RouteCandidate | None:
        matched = next((phrase for phrase in REFUSAL_PHRASES if phrase in text), None)
        if matched is None:
            return None
        if _is_embedded_business_negation(text):
            return None
        return RouteCandidate(
            candidate_id="clarify:no_op",
            candidate_type=CandidateType.CLARIFY,
            target_id="clarify:no_op",
            display_name="No-op clarification",
            source="explicit_signal",
            score=1.0,
            score_breakdown=ScoreBreakdown(keyword=1.0, alias=0.0, semantic=0.0),
            matched_terms=(matched,),
            risk_level="LOW",
            requires_classifier=False,
            reason="User sent explicit no-op or refusal phrase",
        )

    def _resume_candidates(
        self,
        text: str,
        suspended_tasks: Sequence[Mapping[str, Any]],
    ) -> list[RouteCandidate]:
        normalized = text.lower()
        if normalized not in RESUME_PHRASES or len(suspended_tasks) != 1:
            return []
        task = suspended_tasks[0]
        task_id = str(task["id"])
        sop_id = str(task.get("sop_id") or "")
        return [
            RouteCandidate(
                candidate_id=f"suspended:{task_id}",
                candidate_type=CandidateType.SUSPENDED_TASK_RESUME,
                target_id=task_id,
                display_name=f"Resume {sop_id}",
                source="explicit_signal",
                score=0.9,
                score_breakdown=ScoreBreakdown(keyword=0.9, alias=0.0, semantic=0.0),
                matched_terms=(text,),
                risk_level="LOW",
                requires_classifier=False,
                reason="Explicit resume phrase resolved to the single suspended task",
            )
        ]

    def _sop_candidates(
        self,
        text: str,
        active_task: Mapping[str, Any] | None,
        enabled_sop_ids: AbstractSet[str] | None,
    ) -> list[RouteCandidate]:
        candidates: list[RouteCandidate] = []
        for manifest in self._manifests.values():
            if enabled_sop_ids is not None and manifest.sop_id not in enabled_sop_ids:
                continue
            strong = match_strong_trigger_template(text, manifest)
            if strong is not None:
                candidates.append(
                    self._sop_candidate(
                        manifest,
                        score=strong.score,
                        breakdown=ScoreBreakdown(keyword=strong.score, alias=0.0, semantic=0.0),
                        matched_terms=strong.matched_terms,
                        reason=f"Matched strong trigger template: {strong.template_id}",
                        requires_classifier=active_task is not None,
                    )
                )
                continue
            aliases = tuple(term for term in manifest.trigger_keywords if term not in manifest.strong_trigger_keywords)
            alias = self._matched_term(text, aliases)
            if alias is not None:
                candidates.append(
                    self._sop_candidate(
                        manifest,
                        score=0.85,
                        breakdown=ScoreBreakdown(keyword=0.0, alias=0.85, semantic=0.0),
                        matched_terms=(alias,),
                        reason="Configured SOP alias",
                        requires_classifier=True,
                    )
                )
        return candidates

    def _sop_candidate(
        self,
        manifest: SopManifest,
        score: float,
        breakdown: ScoreBreakdown,
        matched_terms: tuple[str, ...],
        reason: str,
        requires_classifier: bool,
    ) -> RouteCandidate:
        return RouteCandidate(
            candidate_id=f"sop:{manifest.sop_id}",
            candidate_type=CandidateType.SOP_INTENT,
            target_id=manifest.sop_id,
            display_name=manifest.display_name,
            source="explicit_signal",
            score=score,
            score_breakdown=breakdown,
            matched_terms=matched_terms,
            risk_level="LOW",
            requires_classifier=requires_classifier,
            reason=reason,
        )

    def _matched_term(self, text: str, terms: Sequence[str]) -> str | None:
        return next((term for term in terms if term and term in text), None)


def _is_embedded_business_negation(text: str) -> bool:
    return any(phrase in text for phrase in ("不用买票", "不用出票", "暂时不用买票", "先不用买票", "先不出票"))
