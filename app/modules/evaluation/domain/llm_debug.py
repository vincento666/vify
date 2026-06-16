from __future__ import annotations

from dataclasses import dataclass
import json

from app.core.errors import BizError, ErrorCode


@dataclass(frozen=True)
class LlmJudgeDebugResult:
    passed: bool
    score: float
    reason: str
    raw_output: str


def build_llm_judge_debug_prompt(
    *,
    prompt_template: str,
    expected_output: str,
    actual_output: str,
) -> str:
    return (
        "LLM_JUDGE_EVALUATION\n"
        "Return strict JSON with keys passed, score, reason.\n\n"
        f"Expected output:\n{expected_output}\n\n"
        f"Actual output:\n{actual_output}\n\n"
        f"Rubric:\n{prompt_template}\n"
    )


def parse_llm_judge_debug_response(raw_output: str, *, passing_score: float) -> LlmJudgeDebugResult:
    try:
        parsed = json.loads(_json_candidate(raw_output))
    except json.JSONDecodeError as exc:
        raise BizError(ErrorCode.BAD_REQUEST, "LLM Judge response is not valid JSON") from exc
    if not isinstance(parsed, dict):
        raise BizError(ErrorCode.BAD_REQUEST, "LLM Judge response must be a JSON object")
    score = round(float(parsed.get("score") or 0.0), 4)
    passed = bool(parsed.get("passed")) and score >= passing_score
    return LlmJudgeDebugResult(
        passed=passed,
        score=score,
        reason=str(parsed.get("reason") or ""),
        raw_output=raw_output,
    )


def _json_candidate(raw_output: str) -> str:
    value = raw_output.strip()
    if value.startswith("```"):
        lines = value.splitlines()
        if lines and lines[0].strip().startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        return "\n".join(lines).strip()
    start = value.find("{")
    end = value.rfind("}")
    if start >= 0 and end > start:
        return value[start : end + 1]
    return value
