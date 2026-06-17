from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SkillManifest:
    name: str
    description: str
    trigger: str


class SkillRegistry:
    def __init__(self, skills: list[SkillManifest] | None = None) -> None:
        self._skills = skills or []

    def list_manifests(self) -> list[SkillManifest]:
        return list(self._skills)
