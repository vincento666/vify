from app.modules.evaluation.domain.llm_debug import build_llm_judge_debug_prompt, parse_llm_judge_debug_response


def test_llm_judge_debug_prompt_contains_contract_and_sample_fields() -> None:
    prompt = build_llm_judge_debug_prompt(
        prompt_template="Grade whether the actual answer follows the refund policy.",
        expected_output="refund policy",
        actual_output="refund policy with details",
    )

    assert "Return strict JSON" in prompt
    assert "passed" in prompt
    assert "score" in prompt
    assert "reason" in prompt
    assert "refund policy with details" in prompt


def test_parse_llm_judge_debug_response_keeps_raw_output_and_threshold() -> None:
    result = parse_llm_judge_debug_response(
        '{"passed": true, "score": 0.82, "reason": "close match"}',
        passing_score=0.9,
    )

    assert result.passed is False
    assert result.score == 0.82
    assert result.reason == "close match"
    assert result.raw_output == '{"passed": true, "score": 0.82, "reason": "close match"}'


def test_parse_llm_judge_debug_response_accepts_fenced_json_from_live_models() -> None:
    result = parse_llm_judge_debug_response(
        '```json\n{"passed": true, "score": 0.91, "reason": "actual preserves expected"}\n```',
        passing_score=0.9,
    )

    assert result.passed is True
    assert result.score == 0.91
    assert result.reason == "actual preserves expected"
