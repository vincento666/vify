from __future__ import annotations

from typing import Any


DEFAULT_EVAL_SET_FIELDS = [
    {"key": "input", "label": "Input", "contentType": "TEXT", "required": True, "displayOrder": 1},
    {"key": "expectedOutput", "label": "Expected output", "contentType": "TEXT", "required": True, "displayOrder": 2},
]


def next_eval_set_version_label(existing_count: int) -> str:
    return f"0.0.{existing_count + 1}"


def build_eval_set_snapshot(
    *,
    fields: list[dict[str, Any]] | None,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    schema = sorted(
        [normalize_field(field) for field in (fields or DEFAULT_EVAL_SET_FIELDS)],
        key=lambda field: (int(field.get("displayOrder") or 0), str(field.get("key") or "")),
    )
    case_snapshot = [_case_snapshot(case) for case in sorted(cases, key=lambda item: int(item["id"]))]
    return {
        "schema": schema,
        "cases": case_snapshot,
        "caseCount": len(case_snapshot),
    }


def normalize_field(field: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": str(field.get("key") or "").strip(),
        "label": str(field.get("label") or field.get("key") or "").strip(),
        "contentType": str(field.get("contentType") or field.get("content_type") or "TEXT").upper(),
        "required": bool(field.get("required")),
        "displayOrder": int(field.get("displayOrder") or field.get("display_order") or 0),
    }


def _case_snapshot(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": int(case["id"]),
        "input": case["input"],
        "expectedOutput": case["expected_output"],
        "tags": list(case.get("tags") or []),
        "metadata": dict(case.get("case_metadata") or {}),
    }
