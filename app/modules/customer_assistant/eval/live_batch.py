from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.modules.customer_assistant.eval.schemas import CustomerAssistantEvalCase


LIVE_BATCH_FLAG = "HIFY_CUSTOMER_ASSISTANT_LIVE_PROMOTION_UAT"
LIVE_MODEL_CONFIG_ID = "HIFY_CUSTOMER_ASSISTANT_LLM_SHADOW_MODEL_CONFIG_ID"


@dataclass(frozen=True)
class LiveBatchResult:
    status: str
    live_model_calls: int = 0
    samples: list[dict[str, Any]] = field(default_factory=list)
    evidence_path: str | None = None
    reason: str = ""


def run_optional_live_batch(
    cases: list[CustomerAssistantEvalCase],
    *,
    env: Mapping[str, str],
    output_dir: Path,
    live_client: Callable[[CustomerAssistantEvalCase, str], dict[str, Any]] | None = None,
) -> LiveBatchResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    enabled = env.get(LIVE_BATCH_FLAG) == "1"
    model_config_id = env.get(LIVE_MODEL_CONFIG_ID, "").strip()

    if not enabled:
        return _skip(output_dir, "skipped: live batch flag is not set to 1")
    if not model_config_id:
        return _skip(output_dir, "skipped: live model config id is missing")
    if live_client is None:
        return _skip(output_dir, "skipped: live client is unavailable")

    samples: list[dict[str, Any]] = []
    for case in cases:
        samples.append(_redact_sample(live_client(case, model_config_id)))
    evidence_path = output_dir / "live-batch-samples.md"
    evidence_path.write_text(_render_samples(samples), encoding="utf-8")
    return LiveBatchResult(
        status="completed",
        live_model_calls=len(samples),
        samples=samples,
        evidence_path=str(evidence_path),
    )


def _skip(output_dir: Path, reason: str) -> LiveBatchResult:
    evidence_path = output_dir / "live-batch-skipped.md"
    evidence_path.write_text(f"# Optional Live Batch\n\n{reason}\n", encoding="utf-8")
    return LiveBatchResult(status="skipped", reason=reason, evidence_path=str(evidence_path))


def _render_samples(samples: list[dict[str, Any]]) -> str:
    lines = ["# Optional Live Batch Samples", ""]
    for sample in samples:
        lines.append(f"- `{sample.get('caseId', 'unknown')}`: {sample.get('status', 'completed')}")
    lines.append("")
    return "\n".join(lines)


def _redact_sample(value: dict[str, Any]) -> dict[str, Any]:
    redacted: dict[str, Any] = {}
    for key, item in value.items():
        lowered = key.lower()
        if "key" in lowered or "token" in lowered or "secret" in lowered:
            redacted[key] = "[REDACTED]"
        else:
            redacted[key] = item
    return redacted
