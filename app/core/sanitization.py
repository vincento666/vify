from __future__ import annotations

import re
from typing import Any

SENSITIVE_KEYS = {"apikey", "secret", "password", "authorization", "bearertoken", "accesstoken", "token"}
SENSITIVE_ASSIGNMENT_RE = re.compile(
    r"(?i)\b(api[-_ ]?key|password|secret|authorization|bearer[-_ ]?token|access[-_ ]?token|token)\s*[:=]\s*([^\s,;]+)"
)
PII_PATTERNS = (
    re.compile(r"\b1[3-9]\d{9}\b"),
    re.compile(r"\b[\w.+-]+@[\w.-]+\.\w+\b"),
    re.compile(r"\b(?:CA|MU|TK|INV)[A-Z0-9-]{3,}\b"),
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
    sanitized = SENSITIVE_ASSIGNMENT_RE.sub(lambda match: f"{match.group(1)}=***", value)
    for pattern in PII_PATTERNS:
        sanitized = pattern.sub("[REDACTED]", sanitized)
    return sanitized


def is_sensitive_key(key: str) -> bool:
    normalized = "".join(ch for ch in key.lower() if ch.isalnum())
    return normalized in SENSITIVE_KEYS
