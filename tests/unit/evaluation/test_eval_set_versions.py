from app.modules.evaluation.domain.versioning import build_eval_set_snapshot, next_eval_set_version_label


def test_next_eval_set_version_label_uses_patch_sequence() -> None:
    assert next_eval_set_version_label(0) == "0.0.1"
    assert next_eval_set_version_label(1) == "0.0.2"
    assert next_eval_set_version_label(12) == "0.0.13"


def test_build_eval_set_snapshot_keeps_field_schema_and_case_data() -> None:
    snapshot = build_eval_set_snapshot(
        fields=[
            {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
            {"key": "expectedOutput", "label": "Expected", "contentType": "TEXT", "required": True, "displayOrder": 2},
        ],
        cases=[
            {"id": 7, "input": "hello", "expected_output": "world", "tags": ["smoke"], "case_metadata": {"locale": "en"}},
        ],
    )

    assert snapshot["schema"][0]["key"] == "input"
    assert snapshot["cases"][0]["id"] == 7
    assert snapshot["cases"][0]["expectedOutput"] == "world"
    assert snapshot["caseCount"] == 1
