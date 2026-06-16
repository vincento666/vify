from __future__ import annotations

from dataclasses import fields, is_dataclass
import re
from typing import Any, Iterable, Mapping

from app.modules.customer_assistant.eval.schemas import (
    CustomerAssistantEvalCase,
    TaskRecognitionEval,
    TimingEval,
)


PHONE_RE = re.compile(r"\b1[3-9]\d{9}\b")
EMAIL_RE = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)


def export_candidate_cases_from_events(
    events: Iterable[Mapping[str, Any]],
) -> list[CustomerAssistantEvalCase]:
    cases: list[CustomerAssistantEvalCase] = []

    for event in events:
        event_type = str(event.get("type", ""))
        payload = _mapping(event.get("payload"))

        if event_type == "llm_shadow_diff_recorded" and payload.get("phase") == "task_recognition":
            command = _first_command(payload.get("baseline")) or _first_command(payload.get("shadow"))
            if command is None:
                continue
            case_id = f"exported-{len(cases) + 1:03d}"
            metadata: dict[str, Any] = {"events": [dict(event)]}
            profile_refs = _profile_refs_from_task_recognition_payload(payload)
            if profile_refs:
                metadata["profileRefs"] = profile_refs
            cases.append(
                CustomerAssistantEvalCase(
                    id=case_id,
                    category=str(payload.get("actor") or "customer"),
                    message=str(payload.get("message") or ""),
                    task_recognition=TaskRecognitionEval(
                        expected_task_key=str(command.get("taskKey") or command.get("task_key") or ""),
                        expected_business_key=_optional_str(
                            command.get("businessKey") or command.get("business_key")
                        ),
                        expected_task_type=_optional_str(command.get("taskType") or command.get("task_type")),
                    ),
                    source="exported",
                    metadata=metadata,
                )
            )
            continue

        if event_type == "recommendation_completed" and cases:
            case = cases[-1]
            cases[-1] = CustomerAssistantEvalCase(
                id=case.id,
                category=case.category,
                message=case.message,
                task_recognition=case.task_recognition,
                recommendation=case.recommendation,
                safety=case.safety,
                timing=TimingEval(
                    run_elapsed_ms=_optional_int(payload.get("elapsedMs") or payload.get("runElapsedMs")),
                    worker_elapsed_ms=case.timing.worker_elapsed_ms,
                    timeout_count=case.timing.timeout_count,
                    failure_count=case.timing.failure_count,
                ),
                source=case.source,
                metadata={**case.metadata, "recommendation_event": dict(event)},
            )
            continue

        if event_type in {"worker_completed", "worker_failed", "run_failed"} and cases:
            case = cases[-1]
            failure_count = case.timing.failure_count + (1 if event_type in {"worker_failed", "run_failed"} else 0)
            cases[-1] = CustomerAssistantEvalCase(
                id=case.id,
                category=case.category,
                message=case.message,
                task_recognition=case.task_recognition,
                recommendation=case.recommendation,
                safety=case.safety,
                timing=TimingEval(
                    run_elapsed_ms=case.timing.run_elapsed_ms,
                    worker_elapsed_ms=_optional_int(payload.get("elapsedMs")) or case.timing.worker_elapsed_ms,
                    timeout_count=case.timing.timeout_count,
                    failure_count=failure_count,
                ),
                source=case.source,
                metadata={**case.metadata, f"{event_type}_event": dict(event)},
            )

    return cases


def redact_case(case: CustomerAssistantEvalCase) -> CustomerAssistantEvalCase:
    return _redact_value(case)


def _redact_value(value: Any) -> Any:
    if isinstance(value, str):
        value = PHONE_RE.sub("[REDACTED_PHONE]", value)
        return EMAIL_RE.sub("[REDACTED_EMAIL]", value)
    if isinstance(value, list):
        return [_redact_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_redact_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _redact_value(item) for key, item in value.items()}
    if is_dataclass(value):
        return type(value)(**{field.name: _redact_value(getattr(value, field.name)) for field in fields(value)})
    return value


def _first_command(value: Any) -> Mapping[str, Any] | None:
    data = _mapping(value)
    commands = data.get("commands")
    if isinstance(commands, list) and commands:
        command = commands[0]
        if isinstance(command, Mapping):
            return command
    return None


def _profile_refs_from_task_recognition_payload(payload: Mapping[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for container_key in ("baseline", "shadow"):
        data = _mapping(payload.get(container_key))
        commands = data.get("commands")
        if not isinstance(commands, list):
            continue
        for command in commands:
            if not isinstance(command, Mapping):
                continue
            profile_refs = _mapping(command.get("profileRefs") or command.get("profile_refs"))
            if profile_refs:
                refs.append(dict(profile_refs))
    return refs


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _optional_str(value: Any) -> str | None:
    return None if value is None else str(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
