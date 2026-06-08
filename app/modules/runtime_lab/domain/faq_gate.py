from dataclasses import dataclass
from collections.abc import Sequence
from typing import Any, Protocol

from app.modules.runtime_lab.domain.router import RouteDecision


class FaqAnswerGate(Protocol):
    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> "FaqAnswerProposal | None":
        ...


class FaqKnowledgeFacade(Protocol):
    def search_context(
        self,
        knowledge_base_id: int,
        query: str,
        top_k: int,
        retrieval_mode: str | None = None,
        score_threshold: float | None = None,
        rerank: bool | None = None,
    ) -> Sequence[Any]:
        ...


@dataclass(frozen=True)
class FaqAnswerEvidence:
    faq_id: int
    question: str
    answer: str
    score: float
    match_type: str
    source: str
    matched_terms: tuple[str, ...] = ()
    knowledge_base_id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "faqId": self.faq_id,
            "question": self.question,
            "answer": self.answer,
            "score": self.score,
            "matchType": self.match_type,
            "source": self.source,
            "matchedTerms": list(self.matched_terms),
        }
        if self.knowledge_base_id is not None:
            payload["knowledgeBaseId"] = self.knowledge_base_id
        return payload


@dataclass(frozen=True)
class FaqAnswerProposal:
    answer: str
    confidence: float
    margin: float
    evidence: FaqAnswerEvidence
    source_layer: str = "faq_exact"
    reason_code: str = "EXACT_MATCH"

    def to_route_decision(self) -> RouteDecision:
        return RouteDecision(
            action="ANSWER_FAQ",
            reason="Exact FAQ accepted before SOP arbitration",
            faq_answer={
                "sourceLayer": self.source_layer,
                "reasonCode": self.reason_code,
                "answer": self.answer,
                "confidence": self.confidence,
                "margin": self.margin,
                "mutatesSopState": False,
                "evidence": self.evidence.to_dict(),
            },
        )


class FaqExactAnswerGate:
    def __init__(
        self,
        knowledge_facade: FaqKnowledgeFacade,
        knowledge_base_ids: Sequence[int],
        *,
        top_k: int = 3,
        keyword_min_score: float = 1.2,
        keyword_min_margin: float = 0.15,
    ) -> None:
        self._knowledge_facade = knowledge_facade
        self._knowledge_base_ids = tuple(int(knowledge_base_id) for knowledge_base_id in knowledge_base_ids)
        self._top_k = top_k
        self._keyword_min_score = keyword_min_score
        self._keyword_min_margin = keyword_min_margin

    def propose(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> FaqAnswerProposal | None:
        del active_task, suspended_tasks
        hits = self._faq_hits(message)
        if not hits:
            return None
        best = hits[0]
        second_score = _score(hits[1]) if len(hits) > 1 else 0.0
        margin = max(0.0, _score(best) - second_score)
        match_type = _match_type(best)
        if match_type == "EXACT":
            confidence = 1.0
            reason_code = "EXACT_MATCH"
        elif _score(best) >= self._keyword_min_score and margin >= self._keyword_min_margin:
            confidence = min(0.99, _score(best) / 2.0)
            reason_code = "KEYWORD_HIGH_CONFIDENCE"
        else:
            return None
        return FaqAnswerProposal(
            answer=_answer(best),
            confidence=confidence,
            margin=margin,
            reason_code=reason_code,
            evidence=FaqAnswerEvidence(
                faq_id=_faq_id(best),
                question=_question(best),
                answer=_answer(best),
                score=_score(best),
                match_type=match_type,
                source="structured_faq",
                matched_terms=(_question(best),),
                knowledge_base_id=_knowledge_base_id(best),
            ),
        )

    def _faq_hits(self, message: str) -> list[Any]:
        hits: list[Any] = []
        for knowledge_base_id in self._knowledge_base_ids:
            for result in self._knowledge_facade.search_context(
                knowledge_base_id,
                message,
                top_k=self._top_k,
                retrieval_mode="keyword",
                score_threshold=None,
                rerank=False,
            ):
                if _source_type(result) != "FAQ":
                    continue
                if _match_type(result) not in {"EXACT", "KEYWORD", "HYBRID"}:
                    continue
                hits.append(_with_knowledge_base_id(result, knowledge_base_id))
        return sorted(hits, key=lambda hit: (-_score(hit), _faq_id(hit)))


def _source_type(result: Any) -> str:
    return str(_field(result, "source_type") or _field(result, "sourceType") or "")


def _match_type(result: Any) -> str:
    return str(_field(result, "match_type") or _field(result, "matchType") or "").upper()


def _score(result: Any) -> float:
    return float(_field(result, "score") or 0.0)


def _question(result: Any) -> str:
    return str(_field(result, "title") or _field(result, "content") or "")


def _answer(result: Any) -> str:
    return str(_field(result, "answer") or _field(result, "content") or "")


def _faq_id(result: Any) -> int:
    return int(_field(result, "faq_id") or _field(result, "faqId") or 0)


def _knowledge_base_id(result: Any) -> int | None:
    raw = _field(result, "_runtime_lab_knowledge_base_id") or _field(result, "knowledge_base_id") or _field(result, "knowledgeBaseId")
    return int(raw) if raw is not None else None


def _with_knowledge_base_id(result: Any, knowledge_base_id: int) -> Any:
    if isinstance(result, dict):
        copied = dict(result)
        copied["_runtime_lab_knowledge_base_id"] = knowledge_base_id
        return copied
    try:
        setattr(result, "_runtime_lab_knowledge_base_id", knowledge_base_id)
    except Exception:
        return result
    return result


def _field(result: Any, name: str) -> Any:
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)
