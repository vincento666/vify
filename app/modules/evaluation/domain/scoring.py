from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from app.core.errors import BizError, ErrorCode

EvaluatorType = Literal["EXACT_MATCH", "CONTAINS_KEYWORDS"]


@dataclass(frozen=True)
class EvaluationSampleResult:
    passed: bool
    score: float
    reason: str


def evaluate_sample(
    evaluator_type: EvaluatorType | str,
    config: dict[str, Any] | None,
    expected_output: str,
    actual_output: str,
) -> EvaluationSampleResult:
    if evaluator_type == "EXACT_MATCH":
        return _evaluate_exact_match(config or {}, expected_output, actual_output)
    if evaluator_type == "CONTAINS_KEYWORDS":
        return _evaluate_contains_keywords(config or {}, actual_output)
    raise BizError(ErrorCode.BAD_REQUEST, f"Unsupported evaluator type: {evaluator_type}")


def _evaluate_exact_match(
    config: dict[str, Any],
    expected_output: str,
    actual_output: str,
) -> EvaluationSampleResult:
    expected = expected_output.strip()
    actual = actual_output.strip()
    if bool(config.get("ignoreCase", False)):
        expected = expected.lower()
        actual = actual.lower()
    passed = expected == actual
    return EvaluationSampleResult(
        passed=passed,
        score=1.0 if passed else 0.0,
        reason="Output exactly matches expected output" if passed else "Output does not exactly match expected output",
    )


def _evaluate_contains_keywords(config: dict[str, Any], actual_output: str) -> EvaluationSampleResult:
    keywords = [str(item).strip() for item in config.get("keywords", []) if str(item).strip()]
    if not keywords:
        raise BizError(ErrorCode.BAD_REQUEST, "Contains Keywords evaluator requires at least one keyword")
    ignore_case = bool(config.get("ignoreCase", True))
    match_mode = str(config.get("matchMode", "all")).lower()
    haystack = actual_output if not ignore_case else actual_output.lower()
    comparable_keywords = keywords if not ignore_case else [keyword.lower() for keyword in keywords]
    matched = [keyword for keyword, comparable in zip(keywords, comparable_keywords, strict=True) if comparable in haystack]
    missing = [keyword for keyword in keywords if keyword not in matched]
    if match_mode == "any":
        passed = len(matched) > 0
    else:
        passed = len(missing) == 0
    score = len(matched) / len(keywords)
    if passed:
        reason = f"Matched keywords: {', '.join(matched)}"
    else:
        reason = f"Missing keywords: {', '.join(missing)}"
    return EvaluationSampleResult(passed=passed, score=round(score, 4), reason=reason)
