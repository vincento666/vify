from typing import Any, Literal

ChatMode = Literal["direct", "rag", "workflow"]


class ChatModeRouter:
    def resolve(self, agent: dict[str, Any]) -> ChatMode:
        if agent.get("workflow_id") is not None:
            return "workflow"
        if agent.get("knowledge_base_id") is not None:
            return "rag"
        return "direct"
