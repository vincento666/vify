from __future__ import annotations

import re
from typing import Any

from app.modules.evaluation.domain.versioning import DEFAULT_EVAL_SET_FIELDS, normalize_field

FIELD_KEY_RE = re.compile(r"^[A-Za-z][A-Za-z0-9_]*$")


def normalize_eval_set_fields(fields: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    raw_fields = fields or DEFAULT_EVAL_SET_FIELDS
    normalized: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, field in enumerate(raw_fields, start=1):
        item = normalize_field({**field, "displayOrder": field.get("displayOrder") or field.get("display_order") or index})
        key = item["key"]
        if not FIELD_KEY_RE.match(key):
            raise ValueError("Eval set field key must start with a letter and contain only letters, numbers, or underscore")
        if key in seen:
            raise ValueError(f"Eval set field duplicate key: {key}")
        seen.add(key)
        normalized.append(item)
    return sorted(normalized, key=lambda item: (int(item["displayOrder"]), item["key"]))


def validate_case_against_fields(
    fields: list[dict[str, Any]],
    *,
    input_value: str,
    expected_output: str,
    metadata: dict[str, Any],
) -> None:
    values = {
        "input": input_value,
        "expectedOutput": expected_output,
        **(metadata or {}),
    }
    for field in fields:
        if not field.get("required"):
            continue
        value = values.get(str(field["key"]))
        if value is None or (isinstance(value, str) and not value.strip()):
            raise ValueError(f"{field.get('label') or field['key']} is required")
