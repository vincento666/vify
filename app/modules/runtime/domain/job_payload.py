from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any


_SENSITIVE_FIELD_NAMES = frozenset(
    {
        "apikey",
        "authorization",
        "bearer",
        "cookie",
        "credential",
        "credentials",
        "password",
        "passwd",
        "secret",
        "token",
    }
)
_SENSITIVE_FIELD_SUFFIXES = (
    "accesstoken",
    "apikey",
    "clientsecret",
    "privatekey",
    "refreshtoken",
    "sessioncookie",
)
_REFERENCE_SUFFIXES = ("ref", "reference", "references")


def validate_durable_job_payload(payload: dict[str, Any]) -> dict[str, Any]:
    """Reject secret-bearing values while preserving explicit secret references."""
    _validate_value(payload)
    return payload


def _validate_value(value: Any) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if _is_sensitive_value_field(str(key)):
                raise ValueError(
                    "Runtime job payload must be secret-free; use a credential reference"
                )
            _validate_value(item)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for item in value:
            _validate_value(item)


def _is_sensitive_value_field(field_name: str) -> bool:
    normalized = "".join(character for character in field_name.lower() if character.isalnum())
    if normalized.endswith(_REFERENCE_SUFFIXES):
        return False
    return normalized in _SENSITIVE_FIELD_NAMES or normalized.endswith(_SENSITIVE_FIELD_SUFFIXES)
