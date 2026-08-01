from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from enum import StrEnum
import json
from typing import Any


class CandidateType(StrEnum):
    ACTIVE_TASK_CONTINUE = "ACTIVE_TASK_CONTINUE"
    SUSPENDED_TASK_RESUME = "SUSPENDED_TASK_RESUME"
    SOP_INTENT = "SOP_INTENT"
    ANSWER_FAQ = "ANSWER_FAQ"
    ANSWER_RAG = "ANSWER_RAG"
    AGENT_FALLBACK = "AGENT_FALLBACK"
    HANDOFF_TO_HUMAN = "HANDOFF_TO_HUMAN"
    CLARIFY = "CLARIFY"
    REJECT_SWITCH_CONTINUE_ACTIVE = "REJECT_SWITCH_CONTINUE_ACTIVE"


@dataclass(frozen=True)
class ScoreBreakdown:
    keyword: float
    alias: float
    semantic: float

    def to_dict(self) -> dict[str, float]:
        return {
            "keyword": self.keyword,
            "alias": self.alias,
            "semantic": self.semantic,
        }


@dataclass(frozen=True)
class RouteCandidate:
    candidate_id: str
    candidate_type: CandidateType | str
    target_id: str
    display_name: str
    source: str
    score: float
    score_breakdown: ScoreBreakdown
    matched_terms: tuple[str, ...]
    risk_level: str
    requires_classifier: bool
    reason: str
    payload: dict[str, Any] | None = None
    source_evidence: tuple[dict[str, Any], ...] = ()
    _canonical_target_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.candidate_type, CandidateType):
            object.__setattr__(self, "candidate_type", CandidateType(str(self.candidate_type)))

    def to_dict(self) -> dict[str, Any]:
        candidate_type = _candidate_type(self.candidate_type)
        payload: dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "candidate_type": candidate_type.value,
            "target_id": self.target_id,
            "display_name": self.display_name,
            "source": self.source,
            "score": self.score,
            "score_breakdown": self.score_breakdown.to_dict(),
            "matched_terms": list(self.matched_terms),
            "risk_level": self.risk_level,
            "requires_classifier": self.requires_classifier,
            "reason": self.reason,
        }
        if self.payload:
            payload["payload"] = dict(self.payload)
        if self.source_evidence:
            payload["sourceEvidence"] = [dict(observation) for observation in self.source_evidence]
        return payload

    @property
    def canonical_key(self) -> str:
        target_id = self._canonical_target_id or self.target_id
        return f"{_candidate_type(self.candidate_type).value}:{target_id}"


class CandidateFusionConflict(ValueError):
    def __init__(
        self,
        canonical_key: str,
        observations: Sequence[dict[str, Any]],
    ) -> None:
        super().__init__(f"Candidate fusion conflict for {canonical_key}")
        self.canonical_key = canonical_key
        self.observations = tuple(dict(observation) for observation in observations)

    def to_clarify_candidate(self) -> RouteCandidate:
        return RouteCandidate(
            candidate_id="clarify:candidate_fusion_conflict",
            candidate_type=CandidateType.CLARIFY,
            target_id="candidate_fusion_conflict",
            display_name="Candidate fusion conflict",
            source="candidate_fusion",
            score=1.0,
            score_breakdown=ScoreBreakdown(keyword=0.0, alias=0.0, semantic=0.0),
            matched_terms=(),
            risk_level="HIGH",
            requires_classifier=False,
            reason="Incompatible payloads share one canonical candidate key",
            payload={
                "candidateFusion": {
                    "outcome": "CONFLICT",
                    "candidateKey": self.canonical_key,
                    "observations": [dict(observation) for observation in self.observations],
                }
            },
            source_evidence=self.observations,
        )


def fuse_candidates(
    candidates: Sequence[RouteCandidate],
    *,
    source_weights: Mapping[str, float] | None = None,
) -> list[RouteCandidate]:
    groups: dict[str, list[RouteCandidate]] = {}
    for candidate in candidates:
        groups.setdefault(candidate.canonical_key, []).append(candidate)
    return [
        _fuse_group(canonical_key, groups[canonical_key], source_weights or {})
        for canonical_key in sorted(groups)
    ]


def select_top_candidates(candidates: list[RouteCandidate], top_k: int) -> list[RouteCandidate]:
    if top_k <= 0:
        return []
    return sorted(
        candidates,
        key=lambda candidate: (-candidate.score, candidate.canonical_key, candidate.candidate_id),
    )[:top_k]


def _fuse_group(
    canonical_key: str,
    group: Sequence[RouteCandidate],
    source_weights: Mapping[str, float],
) -> RouteCandidate:
    weighted = [
        (candidate, _source_weight(candidate, source_weights))
        for candidate in sorted(group, key=_observation_order)
    ]
    observations = [
        _source_observation(canonical_key, candidate, weight)
        for candidate, weight in weighted
    ]
    payloads = {
        _payload_compatibility_signature(candidate)
        for candidate, _weight in weighted
        if candidate.payload
    }
    if len(payloads) > 1:
        raise CandidateFusionConflict(canonical_key, observations)
    winner, winner_weight = min(
        weighted,
        key=lambda item: (
            -float(_source_observation(canonical_key, item[0], item[1])["weightedScore"]),
            _observation_order(item[0]),
        ),
    )
    payload = dict(winner.payload or {})
    winner_observation = _source_observation(canonical_key, winner, winner_weight)
    if winner_weight != 1.0:
        payload["policyWeight"] = {
            "rawScore": winner_observation["rawScore"],
            "sourceWeight": winner_weight,
            "weightedScore": winner_observation["weightedScore"],
        }
    return replace(
        winner,
        score=max(float(observation["weightedScore"]) for observation in observations),
        matched_terms=_stable_terms(candidate for candidate, _weight in weighted),
        risk_level=_highest_risk(candidate.risk_level for candidate, _weight in weighted),
        requires_classifier=any(candidate.requires_classifier for candidate, _weight in weighted),
        payload=payload or None,
        source_evidence=tuple(observations),
    )


def _source_weight(candidate: RouteCandidate, source_weights: Mapping[str, float]) -> float:
    raw = source_weights.get(
        str(candidate.candidate_type),
        source_weights.get(str(candidate.source), source_weights.get("*", 1.0)),
    )
    try:
        return max(0.0, min(5.0, float(raw)))
    except (TypeError, ValueError):
        return 1.0


def _source_observation(
    canonical_key: str,
    candidate: RouteCandidate,
    source_weight: float,
) -> dict[str, Any]:
    raw_score = float(candidate.score)
    return {
        "candidateId": candidate.candidate_id,
        "candidateKey": canonical_key,
        "source": str(candidate.source),
        "rawScore": raw_score,
        "sourceWeight": source_weight,
        "weightedScore": max(0.0, min(1.0, round(raw_score * source_weight, 6))),
    }


def _observation_order(candidate: RouteCandidate) -> tuple[str, str, str, str]:
    return (
        str(candidate.source),
        candidate.candidate_id,
        candidate.display_name,
        str(candidate.reason),
    )


def _stable_terms(candidates: Iterable[RouteCandidate]) -> tuple[str, ...]:
    terms: list[str] = []
    for candidate in candidates:
        for term in candidate.matched_terms:
            if term and term not in terms:
                terms.append(term)
    return tuple(terms)


def _highest_risk(levels: Iterable[str]) -> str:
    rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
    return max((str(level).upper() for level in levels), key=lambda level: rank.get(level, 2), default="HIGH")


def _payload_signature(payload: dict[str, Any] | None) -> str:
    return json.dumps(payload or {}, ensure_ascii=False, sort_keys=True, default=str, separators=(",", ":"))


def _payload_compatibility_signature(candidate: RouteCandidate) -> str:
    payload = candidate.payload or {}
    if _candidate_type(candidate.candidate_type) is CandidateType.ANSWER_FAQ:
        faq_answer = payload.get("faq_answer")
        if isinstance(faq_answer, dict):
            evidence = faq_answer.get("evidence")
            faq_id = evidence.get("faqId") if isinstance(evidence, dict) else None
            answer = faq_answer.get("answer")
            if faq_id is not None and answer:
                return _payload_signature(
                    {
                        "faqAnswer": {
                            "faqId": faq_id,
                            "answer": str(answer),
                            "mutatesSopState": bool(faq_answer.get("mutatesSopState")),
                        }
                    }
                )
    return _payload_signature(payload)


def _candidate_type(value: CandidateType | str) -> CandidateType:
    if isinstance(value, CandidateType):
        return value
    return CandidateType(str(value))
