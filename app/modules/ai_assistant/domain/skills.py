from __future__ import annotations

from dataclasses import dataclass, replace
from hashlib import sha256
import os
from pathlib import Path
import re
from typing import Any


class SkillRuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    trigger: str = ""
    path: str = ""
    version: str = ""
    checksum: str = ""
    risk_level: str = "READ"
    content_loaded: bool = False
    triggers: tuple[str, ...] = ()
    references: tuple[str, ...] = ()
    scripts: tuple[str, ...] = ()
    assets: tuple[str, ...] = ()


@dataclass(frozen=True)
class SkillLoadResult:
    manifest: SkillManifest
    content: str
    audit_events: list[dict[str, Any]]


@dataclass(frozen=True)
class SkillResourceRead:
    skill_name: str
    path: str
    kind: str
    content: str
    checksum: str
    audit_events: list[dict[str, Any]]


@dataclass(frozen=True)
class SkillScriptInvocation:
    skill_name: str
    script_path: str
    status: str
    command: str
    audit_events: list[dict[str, Any]]


class SkillRegistry:
    def __init__(self, skills: list[SkillManifest] | None = None, runtime: SkillRuntime | None = None) -> None:
        self._skills = list(skills or [])
        self._runtime = runtime

    def list_manifests(self) -> list[SkillManifest]:
        return list(self._skills)

    def get_manifest(self, name: str) -> SkillManifest:
        normalized = _normalize_name(name)
        for manifest in self._skills:
            if _normalize_name(manifest.name) == normalized:
                return manifest
        raise SkillRuntimeError(f"Unknown skill: {name}")

    def prompt_index(self) -> str:
        lines: list[str] = []
        for manifest in self._skills:
            parts = [f"{manifest.name}: {manifest.description}"]
            if manifest.trigger:
                parts.append(f"Trigger: {manifest.trigger}")
            if manifest.path:
                parts.append(f"Path: {manifest.path}")
            if manifest.version:
                parts.append(f"Version: {manifest.version}")
            if manifest.checksum:
                parts.append(f"Checksum: {manifest.checksum}")
            parts.append(f"Risk: {manifest.risk_level}")
            lines.append(" ".join(parts))
        return "\n".join(lines)

    def matching_manifests(self, message: str) -> list[SkillManifest]:
        return [manifest for manifest in self._skills if _matches_manifest(manifest, message)]

    def load_for_prompt(self, message: str) -> list[SkillLoadResult]:
        if self._runtime is None:
            return []
        loaded: list[SkillLoadResult] = []
        for manifest in self.matching_manifests(message):
            loaded.append(self._runtime.load_skill(manifest.name, reason="prompt_trigger", session_id=0, run_id=0))
        return loaded


class SkillRuntime:
    def __init__(self, root_paths: list[str | Path] | None = None, *, max_resource_bytes: int = 64_000) -> None:
        self._root_paths = [Path(path).expanduser().resolve() for path in (root_paths or _default_root_paths())]
        self._max_resource_bytes = max(1, int(max_resource_bytes))
        self._manifests: dict[str, SkillManifest] = {}
        self._discovered = False

    @classmethod
    def from_context(cls, context: dict[str, Any] | None) -> SkillRuntime:
        raw = (context or {}).get("aiAssistantSkills")
        roots: list[str | Path] = []
        if isinstance(raw, dict):
            roots = [Path(str(item)) for item in raw.get("rootPaths") or raw.get("roots") or [] if str(item)]
        return cls(root_paths=roots or None)

    def discover(self) -> SkillRegistry:
        manifests: list[SkillManifest] = []
        for root in self._root_paths:
            for skill_dir in _skill_dirs(root):
                skill_file = skill_dir / "SKILL.md"
                metadata = _read_frontmatter(skill_file)
                name = str(metadata.get("name") or skill_dir.name).strip()
                if not name:
                    continue
                triggers = tuple(str(item).strip() for item in metadata.get("triggers", []) if str(item).strip())
                trigger = ", ".join(triggers) if triggers else str(metadata.get("trigger") or name)
                manifest = SkillManifest(
                    name=name,
                    description=str(metadata.get("description") or "").strip(),
                    trigger=trigger,
                    path=str(skill_dir),
                    version=str(metadata.get("version") or "").strip(),
                    checksum=_file_checksum(skill_file),
                    risk_level=str(metadata.get("risk") or metadata.get("risk_level") or "READ").strip().upper(),
                    content_loaded=False,
                    triggers=triggers or (trigger,),
                    references=tuple(_list_relative_files(skill_dir / "references", skill_dir)),
                    scripts=tuple(_list_relative_files(skill_dir / "scripts", skill_dir)),
                    assets=tuple(_list_relative_files(skill_dir / "assets", skill_dir)),
                )
                manifests.append(manifest)
        self._manifests = {_normalize_name(manifest.name): manifest for manifest in sorted(manifests, key=lambda item: item.name)}
        self._discovered = True
        return SkillRegistry(list(self._manifests.values()), runtime=self)

    def load_skill(self, skill_name: str, *, reason: str, session_id: int, run_id: int) -> SkillLoadResult:
        manifest = self._manifest(skill_name)
        skill_file = Path(manifest.path) / "SKILL.md"
        events = [
            _audit_event(
                "skill.load_started",
                session_id=session_id,
                run_id=run_id,
                skill_name=manifest.name,
                payload={
                    "reason": reason,
                    "path": manifest.path,
                    "version": manifest.version,
                    "checksum": manifest.checksum,
                    "riskLevel": manifest.risk_level,
                },
            )
        ]
        content = _read_limited_text(skill_file, self._max_resource_bytes)
        loaded_manifest = replace(manifest, content_loaded=True)
        events.append(
            _audit_event(
                "skill.loaded",
                session_id=session_id,
                run_id=run_id,
                skill_name=manifest.name,
                payload={
                    "path": manifest.path,
                    "version": manifest.version,
                    "checksum": manifest.checksum,
                    "riskLevel": manifest.risk_level,
                    "contentBytes": len(content.encode("utf-8")),
                },
            )
        )
        return SkillLoadResult(manifest=loaded_manifest, content=content, audit_events=events)

    def read_resource(self, skill_name: str, relative_path: str, *, session_id: int, run_id: int) -> SkillResourceRead:
        manifest = self._manifest(skill_name)
        skill_dir = Path(manifest.path).resolve()
        target = _safe_skill_resource_path(skill_dir, relative_path)
        kind = _resource_kind(target, skill_dir)
        if kind is None:
            raise SkillRuntimeError("skill resources must live under references/, scripts/, or assets/")
        content = _read_limited_text(target, self._max_resource_bytes)
        checksum = _file_checksum(target)
        rel = target.relative_to(skill_dir).as_posix()
        return SkillResourceRead(
            skill_name=manifest.name,
            path=rel,
            kind=kind,
            content=content,
            checksum=checksum,
            audit_events=[
                _audit_event(
                    "skill.resource_read",
                    session_id=session_id,
                    run_id=run_id,
                    skill_name=manifest.name,
                    payload={
                        "path": rel,
                        "kind": kind,
                        "checksum": checksum,
                        "bytes": len(content.encode("utf-8")),
                    },
                )
            ],
        )

    def plan_script_invocation(self, skill_name: str, script_path: str, *, session_id: int, run_id: int) -> SkillScriptInvocation:
        resource = self.read_resource(skill_name, script_path, session_id=session_id, run_id=run_id)
        if resource.kind != "script":
            raise SkillRuntimeError("skill script invocation must target scripts/")
        command = f"node {resource.path}"
        event = _audit_event(
            "skill.script_invoked",
            session_id=session_id,
            run_id=run_id,
            skill_name=resource.skill_name,
            payload={
                "scriptPath": resource.path,
                "command": command,
                "status": "PLANNED",
                "throughToolRuntime": True,
            },
        )
        return SkillScriptInvocation(
            skill_name=resource.skill_name,
            script_path=resource.path,
            status="PLANNED",
            command=command,
            audit_events=resource.audit_events + [event],
        )

    def _manifest(self, skill_name: str) -> SkillManifest:
        if not self._discovered:
            self.discover()
        try:
            return self._manifests[_normalize_name(skill_name)]
        except KeyError as exc:
            raise SkillRuntimeError(f"Unknown skill: {skill_name}") from exc


def _default_root_paths() -> list[Path]:
    raw = os.getenv("HIFY_AI_ASSISTANT_SKILL_ROOTS") or ""
    if raw.strip():
        return [Path(item) for item in raw.split(os.pathsep) if item.strip()]
    return [Path.cwd() / ".ai-assistant" / "skills"]


def _skill_dirs(root: Path) -> list[Path]:
    if (root / "SKILL.md").is_file():
        return [root]
    if not root.is_dir():
        return []
    return sorted([path for path in root.iterdir() if path.is_dir() and (path / "SKILL.md").is_file()])


def _read_frontmatter(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    metadata: dict[str, Any] = {}
    current_list_key = ""
    with path.open("r", encoding="utf-8") as handle:
        first = handle.readline()
        if first.strip() != "---":
            return metadata
        for line in handle:
            stripped = line.strip()
            if stripped == "---":
                break
            if stripped.startswith("- ") and current_list_key:
                metadata.setdefault(current_list_key, []).append(stripped[2:].strip())
                continue
            match = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", stripped)
            if not match:
                continue
            key, value = match.group(1), match.group(2)
            normalized_key = key
            if value:
                metadata[normalized_key] = value.strip().strip('"')
                current_list_key = ""
            else:
                metadata[normalized_key] = []
                current_list_key = normalized_key
    if isinstance(metadata.get("trigger"), str) and not metadata.get("triggers"):
        metadata["triggers"] = [str(metadata["trigger"])]
    return metadata


def _file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return f"sha256:{digest.hexdigest()}"


def _read_limited_text(path: Path, max_bytes: int) -> str:
    if not path.is_file():
        raise SkillRuntimeError(f"Skill file not found: {path}")
    content = path.read_bytes()[:max_bytes]
    return content.decode("utf-8", errors="replace")


def _safe_skill_resource_path(skill_dir: Path, relative_path: str) -> Path:
    raw = Path(str(relative_path or "").strip())
    if not str(raw) or raw.is_absolute() or any(part == ".." for part in raw.parts):
        raise SkillRuntimeError("skill resource path must be relative and stay inside the skill directory")
    target = (skill_dir / raw).resolve()
    try:
        target.relative_to(skill_dir.resolve())
    except ValueError as exc:
        raise SkillRuntimeError("skill resource path must stay inside the skill directory") from exc
    return target


def _resource_kind(target: Path, skill_dir: Path) -> str | None:
    rel = target.relative_to(skill_dir).parts
    if not rel:
        return None
    return {"references": "reference", "scripts": "script", "assets": "asset"}.get(rel[0])


def _list_relative_files(directory: Path, skill_dir: Path) -> list[str]:
    if not directory.is_dir():
        return []
    return sorted(path.relative_to(skill_dir).as_posix() for path in directory.rglob("*") if path.is_file())


def _audit_event(
    event_type: str,
    *,
    session_id: int,
    run_id: int,
    skill_name: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "type": event_type,
        "payload": {
            "sessionId": session_id,
            "runId": run_id,
            "skillName": skill_name,
            **payload,
        },
    }


def _matches_manifest(manifest: SkillManifest, message: str) -> bool:
    normalized_message = _normalize_text(message)
    if not normalized_message:
        return False
    candidates = [manifest.name, manifest.trigger, *manifest.triggers]
    for candidate in candidates:
        normalized_candidate = _normalize_text(candidate)
        if not normalized_candidate:
            continue
        if normalized_candidate in normalized_message:
            return True
        words = [word for word in normalized_candidate.split(" ") if len(word) > 2]
        if words and any(word in normalized_message.split(" ") for word in words):
            return True
    return False


def _normalize_name(value: str) -> str:
    return str(value or "").strip().lower().replace("_", "-")


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", str(value or "").strip().lower().replace("_", " "))
