from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistant.domain.skills import SkillRegistry
from app.modules.ai_assistant.domain.tools import ToolRegistry


@dataclass(frozen=True)
class PromptLayer:
    name: str
    content: str


@dataclass(frozen=True)
class PromptMemoryItem:
    scope: str
    key: str
    value: str


@dataclass(frozen=True)
class AssembledPrompt:
    layers: list[dict[str, str]]
    text: str


class PromptAssembler:
    def __init__(
        self,
        base_instruction: str,
        tool_registry: ToolRegistry,
        skill_registry: SkillRegistry | None = None,
    ) -> None:
        self._base_instruction = base_instruction
        self._tool_registry = tool_registry
        self._skill_registry = skill_registry or SkillRegistry()

    def assemble(
        self,
        *,
        user_message: str,
        run_state: dict[str, Any],
        project_instructions: str = "",
        memory_items: list[PromptMemoryItem] | None = None,
        compaction_summary: str = "",
    ) -> AssembledPrompt:
        layers = [PromptLayer("base", self._base_instruction)]
        if project_instructions:
            layers.append(PromptLayer("project_instructions", project_instructions))
        layers.append(
            PromptLayer(
                "tools",
                "\n".join(manifest.name for manifest in self._tool_registry.list_manifests()),
            )
        )
        skill_content = "\n".join(
            f"{manifest.name}: {manifest.description} Trigger: {manifest.trigger}"
            for manifest in self._skill_registry.list_manifests()
        )
        if skill_content:
            layers.append(PromptLayer("skills", skill_content))
        if memory_items:
            layers.append(PromptLayer("memory", _format_memory_items(memory_items)))
        if compaction_summary:
            layers.append(PromptLayer("compaction", compaction_summary))
        layers.extend(
            [
                PromptLayer("run_state", _format_state(run_state)),
                PromptLayer("user_message", user_message),
            ]
        )
        return AssembledPrompt(
            layers=[{"name": layer.name, "content": layer.content} for layer in layers],
            text="\n\n".join(f"[{layer.name}]\n{layer.content}" for layer in layers),
        )


def _format_state(run_state: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in sorted(run_state.items()))


def _format_memory_items(memory_items: list[PromptMemoryItem]) -> str:
    return "\n".join(
        f"{item.scope}.{item.key}: {item.value}"
        for item in sorted(memory_items, key=lambda item: (item.scope, item.key))
    )
