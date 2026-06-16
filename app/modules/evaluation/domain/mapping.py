from __future__ import annotations

from dataclasses import dataclass


TARGET_OUTPUT_FIELD = "__target.output"


@dataclass(frozen=True)
class ExperimentMapping:
    target_field_mapping: dict[str, str]
    evaluator_field_mapping: dict[str, str]
    item_concurrency: int
    item_retry_count: int


def normalize_experiment_mapping(
    *,
    fields: list[str],
    target_field_mapping: dict[str, str] | None,
    evaluator_field_mapping: dict[str, str] | None,
    item_concurrency: int | None,
    item_retry_count: int | None,
) -> ExperimentMapping:
    available = set(fields)
    target = {"userMessage": "input", **(target_field_mapping or {})}
    evaluator = {
        "expectedOutput": "expectedOutput",
        "actualOutput": TARGET_OUTPUT_FIELD,
        **(evaluator_field_mapping or {}),
    }
    for source in list(target.values()) + list(evaluator.values()):
        if source == TARGET_OUTPUT_FIELD:
            continue
        if source not in available:
            raise ValueError(f"Unknown Eval Set field: {source}")
    return ExperimentMapping(
        target_field_mapping={key: str(value) for key, value in target.items()},
        evaluator_field_mapping={key: str(value) for key, value in evaluator.items()},
        item_concurrency=max(1, min(int(item_concurrency or 1), 20)),
        item_retry_count=max(0, min(int(item_retry_count or 0), 5)),
    )
