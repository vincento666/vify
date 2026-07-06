from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any


MEMORY_CONTEXT_KEY = "aiAssistantMemory"


@dataclass(frozen=True)
class InstructionMemory:
    layers: list[dict[str, Any]]
    prompt_text: str


def load_instruction_memory(*, root_path: str | Path, start_path: str | Path | None = None) -> InstructionMemory:
    root = Path(root_path).expanduser().resolve()
    start = Path(start_path or root).expanduser().resolve()
    if start.is_file():
        start = start.parent
    try:
        start.relative_to(root)
    except ValueError:
        start = root

    directories = _directories_from_root(root, start)
    layers: list[dict[str, Any]] = []
    for directory in directories:
        agents_file = directory / "AGENTS.md"
        if not agents_file.exists() or not agents_file.is_file():
            continue
        content = agents_file.read_text(encoding="utf-8")
        layers.append(
            {
                "name": "AGENTS.md",
                "path": str(agents_file),
                "content": content,
                "hash": _hash_text(content),
                "tokenEstimate": estimate_tokens(content),
            }
        )
    prompt_text = "\n\n".join(f"[AGENTS.md:{layer['path']}]\n{layer['content']}" for layer in layers)
    return InstructionMemory(layers=layers, prompt_text=prompt_text)


def memory_payload_from_context(context: dict[str, Any] | None) -> dict[str, Any]:
    raw = (context or {}).get(MEMORY_CONTEXT_KEY)
    payload = deepcopy(raw) if isinstance(raw, dict) else {}
    payload.setdefault("sessionSummary", None)
    payload.setdefault("workingMemory", [])
    payload["workingMemory"] = [dict(item) for item in payload.get("workingMemory") or [] if isinstance(item, dict)]
    return payload


def upsert_session_summary(
    context: dict[str, Any],
    *,
    content: str,
    source_message_ids: list[int],
    source_event_ids: list[int],
    algorithm: str,
    token_estimate: int | None = None,
) -> dict[str, Any]:
    updated = deepcopy(context)
    memory = memory_payload_from_context(updated)
    memory["sessionSummary"] = {
        "content": content,
        "sourceMessageIds": [int(item) for item in source_message_ids],
        "sourceEventIds": [int(item) for item in source_event_ids],
        "algorithm": algorithm,
        "tokenEstimate": int(token_estimate if token_estimate is not None else estimate_tokens(content)),
        "hash": _hash_text(content),
        "updatedAt": _now_iso(),
    }
    updated[MEMORY_CONTEXT_KEY] = memory
    return updated


def upsert_working_memory_item(
    context: dict[str, Any],
    *,
    key: str,
    value: str,
    source: str,
    status: str = "active",
) -> dict[str, Any]:
    updated = deepcopy(context)
    memory = memory_payload_from_context(updated)
    items = [dict(item) for item in memory.get("workingMemory") or [] if item.get("key") != key]
    items.append(
        {
            "key": key,
            "value": value,
            "source": source,
            "status": status,
            "updatedAt": _now_iso(),
        }
    )
    memory["workingMemory"] = items
    updated[MEMORY_CONTEXT_KEY] = memory
    return updated


def invalidate_working_memory_item(context: dict[str, Any], *, key: str, reason: str = "") -> dict[str, Any]:
    updated = deepcopy(context)
    memory = memory_payload_from_context(updated)
    items: list[dict[str, Any]] = []
    for item in memory.get("workingMemory") or []:
        copied = dict(item)
        if copied.get("key") == key and copied.get("status", "active") == "active":
            copied["status"] = "invalidated"
            copied["deleteReason"] = reason
            copied["updatedAt"] = _now_iso()
        items.append(copied)
    memory["workingMemory"] = items
    updated[MEMORY_CONTEXT_KEY] = memory
    return updated


def active_working_memory_items(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    memory = memory_payload_from_context(context)
    return [dict(item) for item in memory.get("workingMemory") or [] if item.get("status", "active") == "active"]


def summary_from_context(context: dict[str, Any] | None) -> dict[str, Any] | None:
    summary = memory_payload_from_context(context).get("sessionSummary")
    return dict(summary) if isinstance(summary, dict) else None


def estimate_tokens(text: str) -> int:
    stripped = str(text or "").strip()
    if not stripped:
        return 0
    return max(1, (len(stripped) + 3) // 4)


def _directories_from_root(root: Path, start: Path) -> list[Path]:
    directories = [root]
    try:
        relative = start.relative_to(root)
    except ValueError:
        return directories
    current = root
    for part in relative.parts:
        current = current / part
        directories.append(current)
    return directories


def _hash_text(content: str) -> str:
    return sha256(content.encode("utf-8")).hexdigest()


def _now_iso() -> str:
    return datetime.now().isoformat()
