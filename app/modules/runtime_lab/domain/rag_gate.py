from collections.abc import Sequence
from dataclasses import dataclass
import re
from typing import Any, Protocol

from app.modules.runtime_lab.domain.router import RouteDecision


class RagKnowledgeFacade(Protocol):
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
class RagContext:
    source_id: str
    title: str
    content: str
    score: float
    match_type: str = ""

    def citation(self) -> dict[str, Any]:
        return {
            "sourceId": self.source_id,
            "title": self.title,
            "score": self.score,
        }


@dataclass(frozen=True)
class RagGenerationResult:
    answer: str
    citations: list[dict[str, Any]]
    generation_evidence: dict[str, Any]


class RagAnswerGeneratorPort(Protocol):
    def generate(self, question: str, contexts: Sequence[RagContext]) -> RagGenerationResult:
        ...


class FakeRagAnswerGenerator:
    model = "fake-rag-generator"

    def generate(self, question: str, contexts: Sequence[RagContext]) -> RagGenerationResult:
        del question
        if not contexts:
            return RagGenerationResult(
                answer="暂未找到足够的资料回答该问题。",
                citations=[],
                generation_evidence={"mode": "fake", "model": self.model, "contextCount": 0},
            )
        primary = contexts[0]
        return RagGenerationResult(
            answer=primary.content,
            citations=[context.citation() for context in contexts],
            generation_evidence={"mode": "fake", "model": self.model, "contextCount": len(contexts)},
        )


class RagAnswerGate:
    def __init__(
        self,
        knowledge_facade: RagKnowledgeFacade,
        knowledge_base_ids: Sequence[int],
        *,
        generator: RagAnswerGeneratorPort | None = None,
        top_k: int = 3,
        retrieval_mode: str = "hybrid",
        rerank: bool = True,
        min_score: float = 0.7,
        lexical_accept_threshold: float = 0.6,
    ) -> None:
        self._knowledge_facade = knowledge_facade
        self._knowledge_base_ids = tuple(int(knowledge_base_id) for knowledge_base_id in knowledge_base_ids)
        self._generator = generator or FakeRagAnswerGenerator()
        self._top_k = top_k
        self._retrieval_mode = retrieval_mode
        self._rerank = rerank
        self._min_score = min_score
        self._lexical_accept_threshold = lexical_accept_threshold

    def decide(
        self,
        message: str,
        *,
        active_task: dict[str, Any] | None,
        suspended_tasks: list[dict[str, Any]],
    ) -> RouteDecision | None:
        del suspended_tasks
        contexts = self._contexts(message)
        if not contexts:
            return None
        if active_task is not None and not _looks_like_question(message):
            return None
        best_context = contexts[0]
        best_score = best_context.score
        lexical_confidence = _lexical_confidence(message, best_context.content)
        policy_confidence = _policy_confidence(
            best_score,
            lexical_confidence,
            self._min_score,
            self._lexical_accept_threshold,
        )
        retrieval_evidence = self._retrieval_evidence(contexts)
        retrieval_evidence["confidenceSignals"] = {
            "topRawScore": best_score,
            "lexicalOverlap": lexical_confidence,
            "minScore": self._min_score,
            "lexicalAcceptThreshold": self._lexical_accept_threshold,
        }
        if best_score < self._min_score and lexical_confidence < self._lexical_accept_threshold:
            return RouteDecision(
                action="CLARIFY",
                reason="RAG retrieval confidence is too low to answer safely",
                rag_answer={
                    "sourceLayer": "rag_policy",
                    "reasonCode": "RAG_LOW_CONFIDENCE",
                    "answer": "",
                    "confidence": policy_confidence,
                    "mutatesSopState": False,
                    "citations": [],
                    "retrievalEvidence": retrieval_evidence,
                    "generationEvidence": {"mode": "not_run", "reason": "low_confidence"},
                },
            )
        if active_task is not None and _active_ambiguous_input(message):
            return RouteDecision(
                action="CLARIFY",
                reason="Active SOP RAG input is ambiguous with slot collection",
                rag_answer={
                    "sourceLayer": "rag_policy",
                    "reasonCode": "RAG_ACTIVE_AMBIGUOUS",
                    "answer": "",
                    "confidence": policy_confidence,
                    "mutatesSopState": False,
                    "citations": [],
                    "retrievalEvidence": retrieval_evidence,
                    "generationEvidence": {"mode": "not_run", "reason": "active_ambiguous"},
                },
            )
        generation = self._generator.generate(message, contexts)
        return RouteDecision(
            action="ANSWER_RAG",
            reason="RAG answer accepted after SOP arbitration",
            rag_answer={
                "sourceLayer": "rag_policy",
                "reasonCode": "RAG_HIGH_CONFIDENCE",
                "answer": generation.answer,
                "confidence": policy_confidence,
                "mutatesSopState": False,
                "citations": generation.citations,
                "retrievalEvidence": retrieval_evidence,
                "generationEvidence": generation.generation_evidence,
            },
        )

    def _contexts(self, message: str) -> list[RagContext]:
        contexts: list[RagContext] = []
        for knowledge_base_id in self._knowledge_base_ids:
            for result in self._knowledge_facade.search_context(
                knowledge_base_id,
                message,
                top_k=self._top_k,
                retrieval_mode=self._retrieval_mode,
                score_threshold=None,
                rerank=self._rerank,
            ):
                if _source_type(result) != "DOCUMENT_CHUNK":
                    continue
                contexts.append(
                    RagContext(
                        source_id=f"chunk:{_chunk_id(result)}",
                        title=_title(result),
                        content=_content(result),
                        score=_score(result),
                        match_type=_match_type(result),
                    )
                )
        return sorted(contexts, key=lambda context: (-context.score, context.source_id))[: self._top_k]

    def _retrieval_evidence(self, contexts: Sequence[RagContext]) -> dict[str, Any]:
        return {
            "retrievalMode": self._retrieval_mode,
            "rerankUsed": self._rerank,
            "topChunks": [
                {
                    "sourceId": context.source_id,
                    "title": context.title,
                    "matchType": context.match_type,
                    "score": context.score,
                    "contentPreview": context.content[:160],
                }
                for context in contexts
            ],
        }


def _source_type(result: Any) -> str:
    return str(_field(result, "source_type") or _field(result, "sourceType") or "")


def _match_type(result: Any) -> str:
    return str(_field(result, "match_type") or _field(result, "matchType") or "")


def _score(result: Any) -> float:
    return float(_field(result, "score") or 0.0)


def _title(result: Any) -> str:
    return str(_field(result, "title") or "")


def _content(result: Any) -> str:
    return str(_field(result, "content") or _field(result, "answer") or "")


def _chunk_id(result: Any) -> int:
    return int(_field(result, "chunk_id") or _field(result, "chunkId") or 0)


def _active_ambiguous_input(message: str) -> bool:
    return _looks_like_question(message) and _looks_like_slot_payload(message)


def _looks_like_question(message: str) -> bool:
    text = message.strip()
    return "?" in text or "？" in text or any(term in text for term in ("怎么", "如何", "吗", "赔", "规则", "怎么办"))


def _looks_like_slot_payload(message: str) -> bool:
    slot_terms = ("订单", "票号", "手机号", "电话", "证件", "身份证", "护照", "乘机人")
    if any(term in message for term in slot_terms):
        return True
    return re.search(r"[A-Za-z]{1,6}-?\d{2,}|\d{6,}", message.strip()) is not None


_LEXICAL_ACCEPT_THRESHOLD = 0.6

_CJK_SIGNAL_TERMS = (
    "航班",
    "延误",
    "超过",
    "小时",
    "保险",
    "理赔",
    "赔付",
    "证明",
    "登机牌",
    "保单",
    "儿童票",
    "退票",
    "改签",
    "手续费",
    "客票",
    "规则",
    "人工",
    "客服",
    "投诉",
    "怎么",
    "如何",
    "怎么办",
)


def _lexical_confidence(question: str, content: str) -> float:
    terms = _query_signal_terms(question)
    if not terms:
        return 0.0
    normalized_content = content.lower()
    hits = sum(1 for term in terms if term in normalized_content)
    return hits / len(terms)


def _policy_confidence(
    raw_score: float,
    lexical_confidence: float,
    min_score: float,
    lexical_accept_threshold: float,
) -> float:
    if raw_score >= min_score:
        return raw_score
    if lexical_confidence >= lexical_accept_threshold:
        scaled = 0.7 + (lexical_confidence - lexical_accept_threshold) * 0.625
        return max(raw_score, min(0.95, scaled))
    return max(raw_score, lexical_confidence)


def _query_signal_terms(value: str) -> set[str]:
    normalized = value.lower()
    terms = set(re.findall(r"[0-9a-zA-Z_]+", normalized))
    terms.update(term for term in _CJK_SIGNAL_TERMS if term in normalized)
    if any(_is_cjk(term) for term in terms):
        return terms
    for span in re.findall(r"[\u4e00-\u9fff]{2,}", normalized):
        if len(span) <= 2:
            terms.add(span)
        else:
            terms.update(span[index : index + 2] for index in range(len(span) - 1))
    return terms


def _is_cjk(value: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in value)


def _field(result: Any, name: str) -> Any:
    if isinstance(result, dict):
        return result.get(name)
    return getattr(result, name, None)
