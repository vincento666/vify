from __future__ import annotations

from dataclasses import dataclass
from datetime import date
import json
import os
import re
from typing import Any, Callable, ContextManager, Protocol

from app.core.config import Settings
from app.modules.ai_assistant.domain.live_model import ChatCompletionClient, LivePlannerConfig
from app.modules.ai_assistant.domain.markdown_memory import (
    MarkdownMemoryStore,
    MemoryConcurrentModificationError,
    ResolvedMemoryScope,
)
from app.modules.ai_assistant.infra.repository import AiAssistantRepository
from app.modules.chat.domain.llm_request import (
    ChatRequestMessage,
    OpenAIChatRequestBuilder,
    ProviderBackedOpenAIChatClient,
    ProviderChatConfig,
)


class MemoryExtractor(Protocol):
    def extract(self, runs: list[dict[str, Any]]) -> list[str]:
        ...


_SECRET_LIKE = re.compile(
    r"(?i)(api[ _-]?key|password|credential|bearer\s+[a-z0-9._-]+|\bsk-[a-z0-9_-]+|secret\s*[:=])"
)


class ModelMemoryExtractor:
    def __init__(
        self,
        config: LivePlannerConfig,
        *,
        client: ChatCompletionClient | None = None,
    ) -> None:
        self._config = config
        auth_config = (
            {"api_key": config.api_key}
            if config.api_key
            else {"api_key_ref": config.api_key_ref}
        )
        self._client = client or ProviderBackedOpenAIChatClient(
            ProviderChatConfig(
                provider_type=config.provider,
                base_url=config.base_url,
                auth_config=auth_config,
            )
        )
        self._builder = OpenAIChatRequestBuilder()

    def extract(self, runs: list[dict[str, Any]]) -> list[str]:
        transcript = [
            {
                "runId": int(run["id"]),
                "user": str((run.get("input_payload") or {}).get("message") or ""),
                "assistant": str((run.get("response_payload") or {}).get("finalAnswer") or ""),
            }
            for run in runs
        ]
        payload = self._builder.build(
            model=self._config.model,
            messages=[
                ChatRequestMessage(
                    role="system",
                    content=(
                        "Extract only durable user preferences, stable facts, decisions, and long-lived constraints. "
                        "Exclude secrets, credentials, hidden reasoning, raw logs, and transient status. "
                        "Return strict JSON: {\"facts\":[\"fact\"]}. Return an empty facts list when nothing is durable."
                    ),
                ),
                ChatRequestMessage(
                    role="user",
                    content=json.dumps(transcript, ensure_ascii=False, separators=(",", ":")),
                ),
            ],
            temperature=0,
            max_tokens=min(512, self._config.max_tokens),
            extra_params={"response_format": {"type": "json_object"}},
        )
        response = self._client.complete(payload)
        content = _first_response_content(response)
        parsed = json.loads(content)
        facts = parsed.get("facts") if isinstance(parsed, dict) else None
        if not isinstance(facts, list):
            raise RuntimeError("memory extractor response must contain a facts list")
        normalized = [" ".join(str(fact).split()) for fact in facts if str(fact).strip()]
        return [fact for fact in normalized if not _SECRET_LIKE.search(fact)]


def create_model_memory_extractor(settings: Settings) -> ModelMemoryExtractor | None:
    api_key = settings.ai_assistant_openrouter_api_key.strip()
    key_name = settings.ai_assistant_openrouter_api_key_env.strip() or "OPENROUTER_API_KEY"
    if not api_key and not os.getenv(key_name, ""):
        return None
    return ModelMemoryExtractor(
        LivePlannerConfig(
            base_url=settings.ai_assistant_openrouter_base_url,
            model=settings.ai_assistant_openrouter_model,
            api_key=api_key,
            api_key_ref=f"env:{key_name}",
            provider="openrouter",
            temperature=0,
            max_tokens=512,
        )
    )


@dataclass(frozen=True)
class MemoryExtractionResult:
    status: str
    batch_key: str | None = None
    run_ids: tuple[int, ...] = ()
    error: str | None = None


class MemoryExtractionCoordinator:
    def __init__(
        self,
        *,
        repository_factory: Callable[[], ContextManager[AiAssistantRepository]],
        store: MarkdownMemoryStore,
        scope: ResolvedMemoryScope,
        extractor: MemoryExtractor,
        today: Callable[[], date] = date.today,
    ) -> None:
        self._repository_factory = repository_factory
        self._store = store
        self._scope = scope
        self._extractor = extractor
        self._today = today

    def process_one(self) -> MemoryExtractionResult:
        with self._repository_factory() as repository:
            batch = repository.claim_memory_extraction_batch()
            runs = (
                repository.get_memory_extraction_runs(list(batch["run_ids"]))
                if batch is not None
                else []
            )
        if batch is None:
            return MemoryExtractionResult(status="PENDING")
        batch_key = str(batch["batch_key"])
        claim_token = str(batch["claim_token"])
        run_ids = tuple(int(run_id) for run_id in batch["run_ids"])
        source_hash = str(batch["source_hash"])
        input_hash = batch.get("input_hash")
        target_hash = batch.get("target_hash")
        try:
            current_hash = self._store.content_hash(self._scope)
            if target_hash and current_hash == target_hash:
                with self._repository_factory() as repository:
                    repository.complete_memory_extraction_batch(
                        batch_key=batch_key,
                        target_hash=str(target_hash),
                        claim_token=claim_token,
                    )
                return MemoryExtractionResult("RECOVERED", batch_key, run_ids)
            if input_hash and current_hash != input_hash:
                with self._repository_factory() as repository:
                    repository.reset_memory_extraction_target(
                        batch_key=batch_key,
                        claim_token=claim_token,
                    )
            if len(runs) != 3:
                raise RuntimeError("memory extraction batch no longer has three completed runs")
            facts = self._extractor.extract(runs)
            plan = self._store.preview_merge_today(
                self._scope,
                facts=facts,
                today=self._today(),
            )
            with self._repository_factory() as repository:
                repository.commit_memory_extraction_plan(
                    batch_key=batch_key,
                    source_hash=source_hash,
                    input_hash=plan.base_hash,
                    target_hash=plan.target_hash,
                    claim_token=claim_token,
                    write=lambda: self._store.replace_planned(self._scope, plan),
                )
            return MemoryExtractionResult("COMPLETED", batch_key, run_ids)
        except MemoryConcurrentModificationError as exc:
            safe_error = _safe_error(exc)
            with self._repository_factory() as repository:
                repository.reset_memory_extraction_target(
                    batch_key=batch_key,
                    claim_token=claim_token,
                )
                repository.fail_memory_extraction_batch(
                    batch_key=batch_key,
                    claim_token=claim_token,
                    error=safe_error,
                )
                _record_failure_event(repository, runs, batch_key, exc)
            return MemoryExtractionResult("FAILED", batch_key, run_ids, safe_error)
        except Exception as exc:
            safe_error = _safe_error(exc)
            with self._repository_factory() as repository:
                repository.fail_memory_extraction_batch(
                    batch_key=batch_key,
                    claim_token=claim_token,
                    error=safe_error,
                )
                _record_failure_event(repository, runs, batch_key, exc)
            return MemoryExtractionResult("FAILED", batch_key, run_ids, safe_error)

    def drain(self) -> list[MemoryExtractionResult]:
        results: list[MemoryExtractionResult] = []
        while True:
            result = self.process_one()
            results.append(result)
            if result.status not in {"COMPLETED", "RECOVERED"}:
                return results


def _first_response_content(response: dict[str, Any]) -> str:
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
        raise RuntimeError("memory extractor response has no choice")
    message = choices[0].get("message")
    if not isinstance(message, dict) or not isinstance(message.get("content"), str):
        raise RuntimeError("memory extractor response has no JSON content")
    return str(message["content"])


def _safe_error(exc: Exception) -> str:
    return type(exc).__name__


def _record_failure_event(
    repository: AiAssistantRepository,
    runs: list[dict[str, Any]],
    batch_key: str,
    exc: Exception,
) -> None:
    if not runs:
        return
    last_run = runs[-1]
    try:
        repository.append_event(
            run_id=int(last_run["id"]),
            session_id=int(last_run["session_id"]),
            event_type="memory.extraction_failed",
            visible_title="记忆提取失败",
            visible_summary="记忆提取失败，已保留批次等待重试。",
            payload={
                "batchKey": batch_key,
                "errorClass": type(exc).__name__,
                "retryable": True,
            },
            status="FAILED",
        )
    except Exception:
        return
