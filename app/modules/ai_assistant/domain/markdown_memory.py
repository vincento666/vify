from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass
from datetime import date, timedelta
import errno
import fcntl
from hashlib import sha256
import inspect
import os
from pathlib import Path
import re
import threading
from typing import Iterator
from uuid import uuid4
import weakref

from app.modules.ai_assistant.domain.memory_context import estimate_tokens


_DATE_HEADING = re.compile(r"^## (\d{4}-\d{2}-\d{2})$")
MAX_DAILY_TOKENS = 100
_SCOPE_LOCK_STRIPES = tuple(threading.RLock() for _ in range(64))
_NOFOLLOW = getattr(os, "O_NOFOLLOW", 0)
_DIRECTORY = getattr(os, "O_DIRECTORY", 0)


class MemoryFormatError(ValueError):
    pass


class MemorySecurityCapabilityError(RuntimeError):
    pass


@dataclass(frozen=True)
class ResolvedMemoryScope:
    _workspace_segment: str
    _user_segment: str
    _authority: object


class MemoryScopeResolver:
    def __init__(self, root_path: str | Path) -> None:
        _require_secure_filesystem()
        self._root = Path(root_path).expanduser().resolve()
        self._root.mkdir(parents=True, exist_ok=True)
        self._root_fd = os.open(
            self._root,
            os.O_RDONLY | _DIRECTORY | _NOFOLLOW,
        )
        self._root_finalizer = weakref.finalize(self, os.close, self._root_fd)
        self._authority = object()

    @property
    def root_path(self) -> Path:
        return self._root

    def resolve(
        self,
        *,
        trusted_user_id: str,
        trusted_workspace_id: str,
    ) -> ResolvedMemoryScope:
        if not trusted_user_id.strip() or not trusted_workspace_id.strip():
            raise ValueError("trusted user and workspace IDs are required")
        return ResolvedMemoryScope(
            _workspace_segment=_scope_segment("workspace", trusted_workspace_id),
            _user_segment=_scope_segment("user", trusted_user_id),
            _authority=self._authority,
        )

    def validate(self, scope: ResolvedMemoryScope) -> None:
        if scope._authority is not self._authority:
            raise ValueError("memory scope was not issued by trusted resolver")

    def lock_key(self, scope: ResolvedMemoryScope) -> str:
        self.validate(scope)
        return f"{self._root}:{scope._workspace_segment}/{scope._user_segment}"

    def duplicate_root_fd(self) -> int:
        if not self._root_finalizer.alive:
            raise RuntimeError("memory scope resolver is closed")
        return os.dup(self._root_fd)

    def close(self) -> None:
        self._root_finalizer()


@dataclass(frozen=True)
class MemoryWindow:
    content: str
    start_line: int | None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class MemoryWriteResult:
    content: str
    day_tokens: int
    dropped_facts: tuple[str, ...] = ()


class MarkdownMemoryStore:
    def __init__(self, resolver: MemoryScopeResolver) -> None:
        self._resolver = resolver
        self._root = resolver.root_path

    def memory_path(self, scope: ResolvedMemoryScope) -> Path:
        self._resolver.validate(scope)
        candidate = (
            self._root
            / scope._workspace_segment
            / scope._user_segment
            / "MEMORY.md"
        )
        try:
            candidate.resolve(strict=False).relative_to(self._root)
        except ValueError as exc:
            raise ValueError("memory path must stay inside configured root") from exc
        return candidate

    def read_recent(
        self,
        scope: ResolvedMemoryScope,
        *,
        today: date,
        days: int = 30,
    ) -> MemoryWindow:
        if days < 1:
            raise ValueError("days must be positive")
        self._resolver.validate(scope)
        try:
            scope_fd = _open_scope_directory_fd(
                self._resolver.duplicate_root_fd(),
                scope,
                create=False,
            )
        except FileNotFoundError:
            return MemoryWindow(content="", start_line=None)
        try:
            try:
                memory_fd = os.open(
                    "MEMORY.md",
                    os.O_RDONLY | _NOFOLLOW,
                    dir_fd=scope_fd,
                )
            except FileNotFoundError:
                return MemoryWindow(content="", start_line=None)
            cutoff = today - timedelta(days=days - 1)
            start_offset: int | None = None
            start_line: int | None = None
            scan_warnings: list[str] = []
            scanned_dates: set[date] = set()
            previous_scanned_date: date | None = None
            with os.fdopen(memory_fd, "rb") as memory_file:
                line_number = 0
                while True:
                    offset = memory_file.tell()
                    raw_line = memory_file.readline()
                    if not raw_line:
                        break
                    line_number += 1
                    stripped = raw_line.decode("utf-8").rstrip("\r\n")
                    heading_date = _heading_date(stripped)
                    if stripped.startswith("## ") and heading_date is None:
                        scan_warnings.append(f"invalid date heading: {stripped}")
                        continue
                    if heading_date is None:
                        continue
                    if heading_date in scanned_dates:
                        scan_warnings.append(f"duplicate date heading: {stripped}")
                        continue
                    if previous_scanned_date is not None and heading_date < previous_scanned_date:
                        scan_warnings.append(f"out-of-order date heading: {stripped}")
                        continue
                    scanned_dates.add(heading_date)
                    previous_scanned_date = heading_date
                    if cutoff <= heading_date <= today:
                        start_offset = offset
                        start_line = line_number
                        break
                if start_offset is None:
                    return MemoryWindow(
                        content="",
                        start_line=None,
                        warnings=tuple(scan_warnings),
                    )
                memory_file.seek(start_offset)
                bounded_content = memory_file.read().decode("utf-8")
        except UnicodeDecodeError as exc:
            raise MemoryFormatError("MEMORY.md must be valid UTF-8") from exc
        finally:
            os.close(scope_fd)
        content, warnings = _valid_window_content(
            bounded_content,
            cutoff=cutoff,
            today=today,
        )
        return MemoryWindow(
            content=content,
            start_line=start_line,
            warnings=tuple(scan_warnings) + warnings,
        )

    def merge_today(
        self,
        scope: ResolvedMemoryScope,
        *,
        facts: list[str],
        today: date,
    ) -> MemoryWriteResult:
        self._resolver.validate(scope)
        scope_fd = _open_scope_directory_fd(
            self._resolver.duplicate_root_fd(),
            scope,
            create=True,
        )
        try:
            with _scope_lock(scope_fd, self._resolver.lock_key(scope)):
                existing = _read_memory_text(scope_fd)
                blocks = _parse_canonical_memory(existing, today=today)
                current = blocks.setdefault(today, [])
                for fact in facts:
                    normalized = " ".join(str(fact).removeprefix("-").strip().split())
                    if normalized and normalized not in current:
                        current.append(normalized)
                dropped_facts = _cap_daily_facts(current)
                content = _render_memory(blocks)
                _atomic_write(scope_fd, content)
                day_content = _daily_content(current)
                measured = estimate_tokens(day_content)
                return MemoryWriteResult(content, measured, dropped_facts)
        finally:
            os.close(scope_fd)


def _scope_segment(kind: str, value: str) -> str:
    return sha256(f"{kind}\0{value.strip()}".encode()).hexdigest()[:24]


def _valid_window_content(
    content: str,
    *,
    cutoff: date,
    today: date,
) -> tuple[str, tuple[str, ...]]:
    selected: list[str] = []
    warnings: list[str] = []
    include_block = False
    seen_dates: set[date] = set()
    previous_date: date | None = None
    for line in content.splitlines(keepends=True):
        if line.startswith("## "):
            stripped = line.rstrip("\r\n")
            heading_date = _heading_date(stripped)
            include_block = False
            if heading_date is None:
                warnings.append(f"invalid date heading: {stripped}")
            elif heading_date in seen_dates:
                warnings.append(f"duplicate date heading: {stripped}")
            elif previous_date is not None and heading_date < previous_date:
                warnings.append(f"out-of-order date heading: {stripped}")
            else:
                seen_dates.add(heading_date)
                previous_date = heading_date
                include_block = cutoff <= heading_date <= today
            if include_block:
                selected.append(line)
            continue
        if include_block:
            selected.append(line)
    rendered = "".join(selected).rstrip() + ("\n" if selected else "")
    return rendered, tuple(warnings)


def _parse_canonical_memory(content: str, *, today: date) -> dict[date, list[str]]:
    if not content:
        return {}
    lines = content.splitlines()
    if not lines or lines[0] != "# Memory":
        raise MemoryFormatError("noncanonical MEMORY.md header")
    blocks: dict[date, list[str]] = {}
    active_date: date | None = None
    previous_date: date | None = None
    for line in lines[1:]:
        if not line:
            continue
        heading_date = _heading_date(line)
        if heading_date is not None:
            if heading_date > today:
                raise MemoryFormatError("noncanonical future date heading")
            if previous_date is not None and heading_date <= previous_date:
                raise MemoryFormatError("noncanonical duplicate or out-of-order date heading")
            active_date = heading_date
            previous_date = heading_date
            blocks[active_date] = []
            continue
        if line.startswith("## "):
            raise MemoryFormatError("noncanonical date heading")
        if active_date is not None and line.startswith("- "):
            fact = " ".join(line[2:].strip().split())
            if not fact:
                raise MemoryFormatError("noncanonical empty memory fact")
            if fact not in blocks[active_date]:
                blocks[active_date].append(fact)
            continue
        raise MemoryFormatError("noncanonical MEMORY.md content")
    for block_date, facts in blocks.items():
        if not facts:
            raise MemoryFormatError("noncanonical empty date block")
        if block_date != today and estimate_tokens(_daily_content(facts)) > MAX_DAILY_TOKENS:
            raise MemoryFormatError("noncanonical historical block exceeds 100 tokens")
    return blocks


def _render_memory(blocks: dict[date, list[str]]) -> str:
    rendered = ["# Memory"]
    for block_date in sorted(blocks):
        facts = blocks[block_date]
        if not facts:
            continue
        rendered.extend(["", f"## {block_date.isoformat()}"])
        rendered.extend(f"- {fact}" for fact in facts)
    return "\n".join(rendered).rstrip() + "\n"


def _daily_content(facts: list[str]) -> str:
    return "\n".join(f"- {fact}" for fact in facts)


def _cap_daily_facts(facts: list[str]) -> tuple[str, ...]:
    original = list(facts)
    kept: list[str] = []
    for fact in reversed(original):
        candidate = [fact, *kept]
        measured = estimate_tokens(_daily_content(candidate))
        if measured <= MAX_DAILY_TOKENS:
            kept = candidate
    facts[:] = kept
    return tuple(fact for fact in original if fact not in kept)


@contextmanager
def _scope_lock(scope_fd: int, lock_key: str) -> Iterator[None]:
    lock_digest = sha256(lock_key.encode()).digest()
    thread_lock = _SCOPE_LOCK_STRIPES[
        int.from_bytes(lock_digest[:2], "big") % len(_SCOPE_LOCK_STRIPES)
    ]
    with thread_lock:
        lock_fd = _open_lock_fd(scope_fd)
        try:
            fcntl.flock(lock_fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(lock_fd, fcntl.LOCK_UN)
            os.close(lock_fd)


def _atomic_write(scope_fd: int, content: str) -> None:
    temporary = f".MEMORY.md.{uuid4().hex}.tmp"
    output_fd: int | None = None
    try:
        output_fd = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
            0o600,
            dir_fd=scope_fd,
        )
        with os.fdopen(output_fd, "w", encoding="utf-8") as output:
            output_fd = None
            output.write(content)
            output.flush()
            os.fsync(output.fileno())
        os.replace(
            temporary,
            "MEMORY.md",
            src_dir_fd=scope_fd,
            dst_dir_fd=scope_fd,
        )
        os.fsync(scope_fd)
    finally:
        if output_fd is not None:
            os.close(output_fd)
        try:
            os.unlink(temporary, dir_fd=scope_fd)
        except FileNotFoundError:
            pass


def _open_lock_fd(scope_fd: int) -> int:
    try:
        return os.open(
            ".MEMORY.md.lock",
            os.O_CREAT | os.O_EXCL | os.O_RDWR,
            0o600,
            dir_fd=scope_fd,
        )
    except FileExistsError:
        return os.open(
            ".MEMORY.md.lock",
            os.O_RDWR | _NOFOLLOW,
            dir_fd=scope_fd,
        )


def _open_scope_directory_fd(
    root_fd: int,
    scope: ResolvedMemoryScope,
    *,
    create: bool,
) -> int:
    current_fd = root_fd
    try:
        for segment in (scope._workspace_segment, scope._user_segment):
            if create:
                try:
                    os.mkdir(segment, mode=0o700, dir_fd=current_fd)
                except FileExistsError:
                    pass
            next_fd = os.open(
                segment,
                os.O_RDONLY | _DIRECTORY | _NOFOLLOW,
                dir_fd=current_fd,
            )
            os.close(current_fd)
            current_fd = next_fd
        return current_fd
    except OSError as exc:
        os.close(current_fd)
        if exc.errno in {errno.ELOOP, errno.ENOTDIR}:
            raise ValueError("memory scope directory must stay inside configured root") from exc
        raise


def _require_secure_filesystem() -> None:
    missing: list[str] = []
    if not _NOFOLLOW:
        missing.append("O_NOFOLLOW")
    if not _DIRECTORY:
        missing.append("O_DIRECTORY")
    if not callable(getattr(fcntl, "flock", None)):
        missing.append("flock")
    for name, function in (
        ("openat", os.open),
        ("mkdirat", os.mkdir),
        ("unlinkat", os.unlink),
    ):
        if function not in os.supports_dir_fd:
            missing.append(name)
    try:
        replace_parameters = set(inspect.signature(os.replace).parameters)
    except (TypeError, ValueError):
        replace_parameters = set()
    if "src_dir_fd" not in replace_parameters or "dst_dir_fd" not in replace_parameters:
        missing.append("renameat")
    if missing:
        raise MemorySecurityCapabilityError(
            f"secure MEMORY.md filesystem capabilities unavailable: {', '.join(missing)}",
        )


def _read_memory_text(scope_fd: int) -> str:
    try:
        memory_fd = os.open(
            "MEMORY.md",
            os.O_RDONLY | _NOFOLLOW,
            dir_fd=scope_fd,
        )
    except FileNotFoundError:
        return ""
    try:
        with os.fdopen(memory_fd, "r", encoding="utf-8") as memory_file:
            return memory_file.read()
    except UnicodeDecodeError as exc:
        raise MemoryFormatError("MEMORY.md must be valid UTF-8") from exc


def _heading_date(line: str) -> date | None:
    match = _DATE_HEADING.fullmatch(line)
    if match is None:
        return None
    try:
        return date.fromisoformat(match.group(1))
    except ValueError:
        return None
