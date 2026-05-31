from collections.abc import Sequence


class PromptBuilder:
    def build(
        self,
        system_prompt: str,
        history: Sequence[dict[str, str]],
        user_message: str,
    ) -> str:
        lines: list[str] = []
        if system_prompt:
            lines.append(f"system: {system_prompt}")
        for message in history:
            lines.append(f"{message['role']}: {message['content']}")
        lines.append(f"user: {user_message}")
        return "\n".join(lines)
