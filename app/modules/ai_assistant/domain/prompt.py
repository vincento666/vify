from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.modules.ai_assistant.domain.tools import ToolRegistry


@dataclass(frozen=True)
class PromptLayer:
    name: str
    content: str


@dataclass(frozen=True)
class AssembledPrompt:
    layers: list[dict[str, str]]
    text: str


class PromptAssembler:
    def __init__(self, base_instruction: str, tool_registry: ToolRegistry) -> None:
        self._base_instruction = base_instruction
        self._tool_registry = tool_registry

    def assemble(self, *, user_message: str, run_state: dict[str, Any]) -> AssembledPrompt:
        layers = [
            PromptLayer("base", self._base_instruction),
            PromptLayer(
                "tools",
                "\n".join(manifest.name for manifest in self._tool_registry.list_manifests()),
            ),
            PromptLayer("run_state", _format_state(run_state)),
            PromptLayer("user_message", user_message),
        ]
        return AssembledPrompt(
            layers=[{"name": layer.name, "content": layer.content} for layer in layers],
            text="\n\n".join(f"[{layer.name}]\n{layer.content}" for layer in layers),
        )


def _format_state(run_state: dict[str, Any]) -> str:
    return "\n".join(f"{key}: {value}" for key, value in sorted(run_state.items()))
