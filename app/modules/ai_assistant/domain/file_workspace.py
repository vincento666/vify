from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
import difflib
import hashlib
import os
from pathlib import Path
import re
import threading
from typing import Any, Iterator
from uuid import uuid4


MAX_TEXT_BYTES = 12000
MAX_LIST_FILES = 200
MAX_SEARCH_MATCHES = 100


@dataclass(frozen=True)
class WorkspaceOperationResult:
    status: str
    output: dict[str, Any]


_LOCKS_GUARD = threading.Lock()
_FILE_LOCKS: dict[str, threading.RLock] = {}


def read_workspace_file(payload: dict[str, Any]) -> WorkspaceOperationResult:
    path = safe_workspace_path(payload, require_path=True)
    rel_path = relative_workspace_path(path)
    if not path.exists() or not path.is_file():
        return WorkspaceOperationResult(
            status="NOT_FOUND",
            output={"path": rel_path, "content": "", "truncated": False},
        )
    content = path.read_text(encoding="utf-8")
    truncated = len(content.encode("utf-8")) > MAX_TEXT_BYTES
    return WorkspaceOperationResult(
        status="COMPLETED",
        output={
            "path": rel_path,
            "content": _truncate_text(content),
            "truncated": truncated,
            **_file_metadata(path),
        },
    )


def list_workspace_files(payload: dict[str, Any]) -> WorkspaceOperationResult:
    base = safe_workspace_path(payload, default_path=".")
    pattern = str(payload.get("pattern") or "**/*")
    max_files = _bounded_int(payload.get("limit"), default=MAX_LIST_FILES, minimum=1, maximum=MAX_LIST_FILES)
    files: list[dict[str, Any]] = []
    truncated = False
    for path in _iter_files(base, pattern):
        if len(files) >= max_files:
            truncated = True
            break
        files.append({"path": relative_workspace_path(path), **_file_metadata(path)})
    return WorkspaceOperationResult(
        status="COMPLETED",
        output={"path": relative_workspace_path(base), "pattern": pattern, "files": files, "truncated": truncated},
    )


def search_workspace_files(payload: dict[str, Any]) -> WorkspaceOperationResult:
    query = str(payload.get("query") or "")
    if not query:
        return _failed(relative_workspace_path(safe_workspace_path(payload, default_path=".")), "INVALID_INPUT", "query is required")
    base = safe_workspace_path(payload, default_path=".")
    pattern = str(payload.get("pattern") or "**/*")
    case_sensitive = bool(payload.get("caseSensitive"))
    max_matches = _bounded_int(
        payload.get("limit"),
        default=MAX_SEARCH_MATCHES,
        minimum=1,
        maximum=MAX_SEARCH_MATCHES,
    )
    needle = query if case_sensitive else query.lower()
    matches: list[dict[str, Any]] = []
    for path in _iter_files(base, pattern):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except UnicodeDecodeError:
            continue
        for line_number, line in enumerate(lines, start=1):
            haystack = line if case_sensitive else line.lower()
            if needle in haystack:
                matches.append({"path": relative_workspace_path(path), "lineNumber": line_number, "lineText": line})
                if len(matches) >= max_matches:
                    return WorkspaceOperationResult(
                        status="COMPLETED",
                        output={
                            "path": relative_workspace_path(base),
                            "query": query,
                            "pattern": pattern,
                            "matches": matches,
                            "truncated": True,
                        },
                    )
    return WorkspaceOperationResult(
        status="COMPLETED",
        output={
            "path": relative_workspace_path(base),
            "query": query,
            "pattern": pattern,
            "matches": matches,
            "truncated": False,
        },
    )


def write_workspace_file(payload: dict[str, Any]) -> WorkspaceOperationResult:
    path = safe_workspace_path(payload, require_path=True)
    content = str(payload.get("content") or "")
    with file_lock(path):
        failed = _check_preconditions(path, payload)
        if failed is not None:
            return failed
        previous_text = _read_existing_text(path)
        diff_preview = _diff_preview(relative_workspace_path(path), previous_text, content)
        if bool(payload.get("dryRun")):
            return WorkspaceOperationResult(
                status="PREVIEW",
                output=_write_output(path, previous_text, content, diff_preview, rollback_snapshot=None) | {"changed": previous_text != content},
            )
        rollback_snapshot = _write_rollback_snapshot(path, previous_text) if path.exists() else None
        _atomic_write(path, content)
        return WorkspaceOperationResult(
            status="COMPLETED",
            output=_write_output(path, previous_text, content, diff_preview, rollback_snapshot=rollback_snapshot),
        )


def edit_workspace_file(payload: dict[str, Any]) -> WorkspaceOperationResult:
    path = safe_workspace_path(payload, require_path=True)
    old_text = str(payload.get("oldText") or "")
    new_text = str(payload.get("newText") or "")
    if not old_text:
        return _failed(relative_workspace_path(path), "INVALID_INPUT", "oldText is required")
    with file_lock(path):
        if not path.exists() or not path.is_file():
            return WorkspaceOperationResult(status="NOT_FOUND", output={"path": relative_workspace_path(path)})
        failed = _check_preconditions(path, payload)
        if failed is not None:
            return failed
        previous_text = path.read_text(encoding="utf-8")
        replacement = _replace_unique(previous_text, payload | {"oldText": old_text, "newText": new_text})
        if isinstance(replacement, WorkspaceOperationResult):
            return replacement
        next_text, candidate_count = replacement
        diff_preview = _diff_preview(relative_workspace_path(path), previous_text, next_text)
        if bool(payload.get("dryRun")):
            return WorkspaceOperationResult(
                status="PREVIEW",
                output=_write_output(path, previous_text, next_text, diff_preview, rollback_snapshot=None)
                | {"candidateCount": candidate_count, "changed": previous_text != next_text},
            )
        rollback_snapshot = _write_rollback_snapshot(path, previous_text)
        _atomic_write(path, next_text)
        return WorkspaceOperationResult(
            status="COMPLETED",
            output=_write_output(path, previous_text, next_text, diff_preview, rollback_snapshot=rollback_snapshot)
            | {"candidateCount": candidate_count},
        )


def apply_workspace_patch(payload: dict[str, Any]) -> WorkspaceOperationResult:
    path = safe_workspace_path(payload, require_path=True)
    operations = payload.get("operations")
    if not isinstance(operations, list) or not operations:
        return _failed(relative_workspace_path(path), "INVALID_INPUT", "operations must be a non-empty list")
    with file_lock(path):
        if not path.exists() or not path.is_file():
            return WorkspaceOperationResult(status="NOT_FOUND", output={"path": relative_workspace_path(path)})
        failed = _check_preconditions(path, payload)
        if failed is not None:
            return failed
        previous_text = path.read_text(encoding="utf-8")
        next_text = previous_text
        for operation in operations:
            if not isinstance(operation, dict):
                return _failed(relative_workspace_path(path), "INVALID_INPUT", "operation must be an object")
            replacement = _replace_unique(next_text, operation | {"path": relative_workspace_path(path)})
            if isinstance(replacement, WorkspaceOperationResult):
                return replacement
            next_text = replacement[0]
        diff_preview = _diff_preview(relative_workspace_path(path), previous_text, next_text)
        if bool(payload.get("dryRun")):
            return WorkspaceOperationResult(
                status="PREVIEW",
                output=_write_output(path, previous_text, next_text, diff_preview, rollback_snapshot=None)
                | {"operationCount": len(operations), "changed": previous_text != next_text},
            )
        rollback_snapshot = _write_rollback_snapshot(path, previous_text)
        _atomic_write(path, next_text)
        return WorkspaceOperationResult(
            status="COMPLETED",
            output=_write_output(path, previous_text, next_text, diff_preview, rollback_snapshot=rollback_snapshot)
            | {"operationCount": len(operations)},
        )


def workspace_root() -> Path:
    return Path(os.getenv("HIFY_WORKSPACE_ROOT") or Path.cwd()).resolve()


def safe_workspace_path(
    payload: dict[str, Any],
    *,
    default_path: str | None = None,
    require_path: bool = False,
) -> Path:
    raw = str(payload.get("path") or default_path or "").strip()
    if require_path and not raw:
        raise ValueError("path is required")
    raw = raw or "."
    root = workspace_root()
    candidate = (root / raw).resolve()
    if candidate != root and root not in candidate.parents:
        raise ValueError("path must stay inside workspace")
    return candidate


def relative_workspace_path(path: Path) -> str:
    root = workspace_root()
    resolved = path.resolve()
    if resolved == root:
        return "."
    return resolved.relative_to(root).as_posix()


@contextmanager
def file_lock(path: Path) -> Iterator[None]:
    lock_key = str(path.resolve())
    with _LOCKS_GUARD:
        lock = _FILE_LOCKS.setdefault(lock_key, threading.RLock())
    with lock:
        yield


def _iter_files(base: Path, pattern: str) -> Iterator[Path]:
    if base.is_file() and not _is_internal_path(base):
        yield base
        return
    if not base.exists() or not base.is_dir():
        return
    candidates = base.rglob(pattern) if "**" not in pattern else base.glob(pattern)
    for path in sorted(candidates, key=lambda item: relative_workspace_path(item)):
        if path.is_file() and not _is_internal_path(path):
            yield path


def _is_internal_path(path: Path) -> bool:
    return ".ai-assistant" in path.relative_to(workspace_root()).parts


def _file_metadata(path: Path) -> dict[str, Any]:
    stat = path.stat()
    content = path.read_bytes()
    return {
        "checksum": hashlib.sha256(content).hexdigest(),
        "mtimeNs": int(stat.st_mtime_ns),
        "sizeBytes": int(stat.st_size),
    }


def _check_preconditions(path: Path, payload: dict[str, Any]) -> WorkspaceOperationResult | None:
    expected_checksum = str(payload.get("expectedChecksum") or "").strip()
    expected_mtime = payload.get("expectedMtimeNs")
    metadata = _file_metadata(path) if path.exists() and path.is_file() else None
    actual_checksum = str(metadata.get("checksum") if metadata else "")
    actual_mtime = int(metadata["mtimeNs"]) if metadata else 0
    rel_path = relative_workspace_path(path)
    if expected_checksum and expected_checksum != actual_checksum:
        return WorkspaceOperationResult(
            status="PRECONDITION_FAILED",
            output={
                "path": rel_path,
                "error": {
                    "code": "CHECKSUM_MISMATCH",
                    "message": "expectedChecksum does not match current file checksum",
                },
                "expectedChecksum": expected_checksum,
                "actualChecksum": actual_checksum,
            },
        )
    expected_mtime_int = int(str(expected_mtime)) if expected_mtime not in (None, "") else None
    if expected_mtime_int is not None and expected_mtime_int != actual_mtime:
        return WorkspaceOperationResult(
            status="PRECONDITION_FAILED",
            output={
                "path": rel_path,
                "error": {
                    "code": "MTIME_MISMATCH",
                    "message": "expectedMtimeNs does not match current file mtime",
                },
                "expectedMtimeNs": expected_mtime_int,
                "actualMtimeNs": actual_mtime,
            },
        )
    return None


def _replace_unique(content: str, payload: dict[str, Any]) -> tuple[str, int] | WorkspaceOperationResult:
    old_text = str(payload.get("oldText") or "")
    new_text = str(payload.get("newText") or "")
    rel_path = str(payload.get("path") or "")
    if not old_text:
        return _failed(rel_path, "INVALID_INPUT", "oldText is required")
    matches = _find_matches(
        content,
        old_text,
        before_context=str(payload.get("beforeContext") or ""),
        after_context=str(payload.get("afterContext") or ""),
        whitespace_tolerant=bool(payload.get("whitespaceTolerant")),
    )
    if not matches:
        return _failed(rel_path, "NO_MATCH", "oldText did not match the current file")
    if len(matches) > 1:
        return _failed(rel_path, "NON_UNIQUE_MATCH", "oldText matched more than one candidate")
    start, end = matches[0]
    return content[:start] + new_text + content[end:], len(matches)


def _find_matches(
    content: str,
    old_text: str,
    *,
    before_context: str,
    after_context: str,
    whitespace_tolerant: bool,
) -> list[tuple[int, int]]:
    if not whitespace_tolerant:
        matches: list[tuple[int, int]] = []
        start = 0
        while True:
            index = content.find(old_text, start)
            if index < 0:
                break
            matches.append((index, index + len(old_text)))
            start = index + max(1, len(old_text))
    else:
        pattern = _whitespace_tolerant_pattern(old_text)
        matches = [(match.start(), match.end()) for match in re.finditer(pattern, content, flags=re.MULTILINE)]
    return [
        (start, end)
        for start, end in matches
        if (not before_context or content[:start].endswith(before_context))
        and (not after_context or content[end:].startswith(after_context))
    ]


def _whitespace_tolerant_pattern(text: str) -> str:
    tokens = re.split(r"(\s+)", text)
    return "".join(r"\s+" if token.isspace() else re.escape(token) for token in tokens if token)


def _write_output(
    path: Path,
    previous_text: str,
    next_text: str,
    diff_preview: str,
    *,
    rollback_snapshot: dict[str, Any] | None,
) -> dict[str, Any]:
    encoded_next = next_text.encode("utf-8")
    output = {
        "path": relative_workspace_path(path),
        "bytes": len(encoded_next),
        "previousChecksum": _text_checksum(previous_text),
        "checksum": _text_checksum(next_text),
        "diffPreview": diff_preview,
        "atomic": True,
        "lock": {"mode": "WRITE", "scope": "process", "resource": relative_workspace_path(path)},
    }
    if rollback_snapshot is not None:
        output["rollbackSnapshot"] = rollback_snapshot
    return output


def _write_rollback_snapshot(path: Path, previous_text: str) -> dict[str, Any]:
    snapshot_root = workspace_root() / ".ai-assistant" / "rollback"
    snapshot_root.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "_", relative_workspace_path(path))
    snapshot_path = snapshot_root / f"{safe_name}.{uuid4().hex}.bak"
    snapshot_path.write_text(previous_text, encoding="utf-8")
    return {
        "path": relative_workspace_path(snapshot_path),
        "checksum": _text_checksum(previous_text),
        "sizeBytes": len(previous_text.encode("utf-8")),
    }


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink()


def _read_existing_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    return path.read_text(encoding="utf-8")


def _diff_preview(path: str, before: str, after: str) -> str:
    diff = difflib.unified_diff(
        before.splitlines(),
        after.splitlines(),
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    return _truncate_text("\n".join(diff))


def _truncate_text(text: str) -> str:
    encoded = text.encode("utf-8")
    if len(encoded) <= MAX_TEXT_BYTES:
        return text
    return encoded[:MAX_TEXT_BYTES].decode("utf-8", errors="ignore")


def _text_checksum(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _bounded_int(value: Any, *, default: int, minimum: int, maximum: int) -> int:
    try:
        resolved = int(value)
    except (TypeError, ValueError):
        resolved = default
    return max(minimum, min(maximum, resolved))


def _failed(path: str, code: str, message: str) -> WorkspaceOperationResult:
    return WorkspaceOperationResult(
        status="FAILED",
        output={"path": path, "error": {"code": code, "message": message}},
    )
