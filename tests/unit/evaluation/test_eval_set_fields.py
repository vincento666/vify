import pytest

from app.modules.evaluation.domain.fields import normalize_eval_set_fields, validate_case_against_fields


def test_normalize_eval_set_fields_orders_and_deduplicates_keys() -> None:
    fields = normalize_eval_set_fields([
        {"key": "reference_output", "label": "Reference", "contentType": "text", "required": True, "displayOrder": 3},
        {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
    ])

    assert [field["key"] for field in fields] == ["input", "reference_output"]
    assert fields[1]["contentType"] == "TEXT"
    assert fields[1]["required"] is True


def test_normalize_eval_set_fields_rejects_duplicate_or_reserved_invalid_fields() -> None:
    with pytest.raises(ValueError, match="duplicate"):
        normalize_eval_set_fields([
            {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
            {"key": "input", "label": "Input copy", "contentType": "TEXT", "required": False, "displayOrder": 2},
        ])
    with pytest.raises(ValueError, match="key"):
        normalize_eval_set_fields([
            {"key": "bad key", "label": "Bad", "contentType": "TEXT", "required": False, "displayOrder": 1},
        ])


def test_validate_case_against_required_dynamic_fields() -> None:
    fields = normalize_eval_set_fields([
        {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
        {"key": "expectedOutput", "label": "Expected", "contentType": "TEXT", "required": True, "displayOrder": 2},
        {"key": "reference_output", "label": "Reference", "contentType": "TEXT", "required": True, "displayOrder": 3},
    ])

    with pytest.raises(ValueError, match="Reference"):
        validate_case_against_fields(fields, input_value="hello", expected_output="world", metadata={})

    validate_case_against_fields(
        fields,
        input_value="hello",
        expected_output="world",
        metadata={"reference_output": "docs paragraph"},
    )
