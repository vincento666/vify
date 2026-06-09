from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = {"apikey", "secret", "password", "authorization", "bearertoken", "accesstoken"}
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[-_ ]?key|password|secret|authorization|bearer[-_ ]?token|access[-_ ]?token)\s*[:=]\s*([^\s,;]+)"
)


def sanitize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            key: "***" if is_sensitive_key(str(key)) else sanitize_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, str):
        return sanitize_text(value)
    return value


def sanitize_text(value: str) -> str:
    return SENSITIVE_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=***", value)


def is_sensitive_key(key: str) -> bool:
    normalized = "".join(ch for ch in key.lower() if ch.isalnum())
    return normalized in SENSITIVE_KEYS
