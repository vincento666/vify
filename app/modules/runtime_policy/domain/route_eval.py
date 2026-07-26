from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import dataclass
from typing import Any

RuntimeRouteReplayPort = Callable[
    [dict[str, Any], dict[str, Any]],
    dict[str, Any],
]


@dataclass(frozen=True)
class RouteEvalCase:
    case_id: str
    case_version: int
    status: str
    turns: tuple[dict[str, Any], ...]
    initial_route_context: dict[str, Any]
    enabled_intent_ids: tuple[str, ...]
    policy_snapshot: dict[str, Any]
    classifier_fixture: dict[str, Any]
    expected: dict[str, Any]
    _present_fields: frozenset[str]
    _expected_present_fields: frozenset[str]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> "RouteEvalCase":
        case_version = _positive_int_or_zero(payload.get("caseVersion"))
        raw_turns = payload.get("turns")
        turns = raw_turns if isinstance(raw_turns, list | tuple) else []
        raw_enabled_intent_ids = payload.get("enabledIntentIds")
        enabled_intent_ids = (
            raw_enabled_intent_ids
            if isinstance(raw_enabled_intent_ids, list | tuple)
            else []
        )
        raw_expected = payload.get("expected")
        expected_fields = (
            raw_expected.keys()
            if isinstance(raw_expected, Mapping)
            else ()
        )
        return cls(
            case_id=str(payload.get("caseId") or "").strip(),
            case_version=case_version,
            status=str(payload.get("status") or "required"),
            turns=tuple(
                deepcopy(dict(turn))
                for turn in turns or []
                if isinstance(turn, Mapping)
            ),
            initial_route_context=_mapping_copy(payload.get("initialRouteContext")),
            enabled_intent_ids=tuple(
                str(intent_id)
                for intent_id in enabled_intent_ids
            ),
            policy_snapshot=_mapping_copy(payload.get("policySnapshot")),
            classifier_fixture=_mapping_copy(payload.get("classifierFixture")),
            expected=_mapping_copy(payload.get("expected")),
            _present_fields=frozenset(str(key) for key in payload),
            _expected_present_fields=frozenset(
                str(key) for key in expected_fields
            ),
        )

    def validation_errors(self) -> list[str]:
        errors: list[str] = []
        if not self.case_id:
            errors.append("caseId.required")
        if self.case_version < 1:
            errors.append("caseVersion.invalid")
        if self.status not in {"required", "known_gap"}:
            errors.append("status.invalid")
        if not self.turns:
            errors.append("turns.required")
        if self.status in {"required", "known_gap"}:
            for field, error in (
                ("initialRouteContext", "initialRouteContext.required"),
                ("enabledIntentIds", "enabledIntentIds.required"),
                ("policySnapshot", "policySnapshot.required"),
                ("classifierFixture", "classifierFixture.required"),
            ):
                if field not in self._present_fields:
                    errors.append(error)
        if not str(self.expected.get("finalAction") or "").strip():
            errors.append("expected.finalAction.required")
        if "mutatesTaskState" not in self.expected:
            errors.append("expected.mutatesTaskState.required")
        if self.status in {"required", "known_gap"}:
            for field, error in (
                ("recalledCandidateIds", "expected.recalledCandidateIds.required"),
                ("targetId", "expected.targetId.required"),
                ("clarificationQuestion", "expected.clarificationQuestion.required"),
            ):
                if field not in self._expected_present_fields:
                    errors.append(error)
        return errors

    def to_payload(self) -> dict[str, Any]:
        return {
            "caseId": self.case_id,
            "caseVersion": self.case_version,
            "status": self.status,
            "turns": deepcopy(list(self.turns)),
            "initialRouteContext": deepcopy(self.initial_route_context),
            "enabledIntentIds": list(self.enabled_intent_ids),
            "policySnapshot": deepcopy(self.policy_snapshot),
            "classifierFixture": deepcopy(self.classifier_fixture),
            "expected": deepcopy(self.expected),
        }


def _mapping_copy(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        return {}
    return deepcopy(dict(value))


def _positive_int_or_zero(value: object) -> int:
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
