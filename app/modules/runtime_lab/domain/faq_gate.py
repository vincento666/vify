from collections.abc import Sequence
from dataclasses import dataclass
import re
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


class FaqSemanticAnswerGate:
    def __init__(
        self,
        knowledge_facade: FaqKnowledgeFacade,
        knowledge_base_ids: Sequence[int],
        *,
        top_k: int = 5,
        rerank: bool = True,
        min_score: float = 0.85,
        min_margin: float = 0.12,
    ) -> None:
        self._knowledge_facade = knowledge_facade
        self._knowledge_base_ids = tuple(int(knowledge_base_id) for knowledge_base_id in knowledge_base_ids)
        self._top_k = top_k
        self._rerank = rerank
        self._min_score = min_score
        self._min_margin = min_margin

    def decide(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        del suspended_tasks
        hits = self._semantic_hits(message)
        if not hits:
            return None
        best = hits[0]
        second_score = _score(hits[1]) if len(hits) > 1 else 0.0
        margin = max(0.0, _score(best) - second_score)
        if _score(best) < self._min_score:
            return None
        if active_task is not None and not _semantic_looks_like_question(message):
            return None
        if active_task is not None and _semantic_active_ambiguous_input(message):
            return RouteDecision(
                action="CLARIFY",
                reason="Active SOP semantic FAQ input is ambiguous with slot collection",
                faq_answer={
                    "sourceLayer": "faq_semantic",
                    "reasonCode": "SEMANTIC_ACTIVE_AMBIGUOUS",
                    "answer": _answer(best),
                    "confidence": min(0.99, _score(best)),
                    "margin": margin,
                    "mutatesSopState": False,
                    "evidence": _semantic_evidence(best, hits, retrieval_mode="faq", rerank_used=self._rerank),
                },
            )
        if margin < self._min_margin:
            return RouteDecision(
                action="CLARIFY",
                reason="Semantic FAQ candidates are too close to answer safely",
                faq_answer={
                    "sourceLayer": "faq_semantic",
                    "reasonCode": "SEMANTIC_LOW_MARGIN",
                    "answer": _answer(best),
                    "confidence": min(0.99, _score(best)),
                    "margin": margin,
                    "mutatesSopState": False,
                    "evidence": _semantic_evidence(best, hits, retrieval_mode="faq", rerank_used=self._rerank),
                },
            )
        return RouteDecision(
            action="ANSWER_FAQ",
            reason="Semantic FAQ accepted before SOP arbitration",
            faq_answer={
                "sourceLayer": "faq_semantic",
                "reasonCode": "SEMANTIC_HIGH_CONFIDENCE",
                "answer": _answer(best),
                "confidence": min(0.99, _score(best)),
                "margin": margin,
                "mutatesSopState": False,
                "evidence": _semantic_evidence(best, hits, retrieval_mode="faq", rerank_used=self._rerank),
            },
        )

    def _semantic_hits(self, message: str) -> list[Any]:
        hits: list[Any] = []
        for knowledge_base_id in self._knowledge_base_ids:
            for result in self._knowledge_facade.search_context(
                knowledge_base_id,
                message,
                top_k=self._top_k,
                retrieval_mode="faq",
                score_threshold=None,
                rerank=self._rerank,
            ):
                if _source_type(result) != "FAQ":
                    continue
                if _match_type(result) not in {"VECTOR", "HYBRID"}:
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


def _semantic_evidence(
    result: Any,
    hits: Sequence[Any],
    *,
    retrieval_mode: str,
    rerank_used: bool,
) -> dict[str, Any]:
    evidence = FaqAnswerEvidence(
        faq_id=_faq_id(result),
        question=_question(result),
        answer=_answer(result),
        score=_score(result),
        match_type=_match_type(result),
        source="structured_faq",
        matched_terms=(),
        knowledge_base_id=_knowledge_base_id(result),
    ).to_dict()
    evidence["retrievalMode"] = retrieval_mode
    evidence["rerankUsed"] = rerank_used
    evidence["topCandidates"] = [
        {
            "faqId": _faq_id(hit),
            "question": _question(hit),
            "score": _score(hit),
            "matchType": _match_type(hit),
            "knowledgeBaseId": _knowledge_base_id(hit),
        }
        for hit in hits
    ]
    return evidence


def _semantic_active_ambiguous_input(message: str) -> bool:
    return _semantic_looks_like_question(message) and _semantic_looks_like_slot_payload(message)


def _semantic_looks_like_question(message: str) -> bool:
    text = message.strip()
    return "?" in text or "？" in text or any(term in text for term in ("可以", "能", "怎么", "如何", "吗", "规则"))


def _semantic_looks_like_slot_payload(message: str) -> bool:
    slot_terms = ("订单", "票号", "手机号", "电话", "证件", "身份证", "护照", "乘机人")
    if any(term in message for term in slot_terms):
        return True
    return re.search(r"[A-Za-z]{1,6}-?\d{2,}|\d{6,}", message.strip()) is not None


def _field(result: Any, name: str) -> Any:
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)
