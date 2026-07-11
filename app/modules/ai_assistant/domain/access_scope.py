from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import os
from pathlib import Path


@dataclass(frozen=True)
class AiAssistantAccessScope:
    user_id: str
    workspace_id: str

    def __post_init__(self) -> None:
        normalized_user = self.user_id.strip()
        normalized_workspace = self.workspace_id.strip()
        if not normalized_user or not normalized_workspace:
            raise ValueError("AI Assistant user and workspace scope are required")
        object.__setattr__(self, "user_id", normalized_user)
        object.__setattr__(self, "workspace_id", normalized_workspace)


def access_scope_for_workspace(
    *,
    trusted_user_id: str,
    trusted_workspace_root: str | Path,
) -> AiAssistantAccessScope:
    workspace_root = Path(trusted_workspace_root).expanduser().resolve()
    workspace_id = sha256(str(workspace_root).encode()).hexdigest()
    return AiAssistantAccessScope(
        user_id=trusted_user_id,
        workspace_id=workspace_id,
    )


def local_ai_assistant_scope() -> AiAssistantAccessScope:
    return access_scope_for_workspace(
        trusted_user_id="local-user",
        trusted_workspace_root=os.environ.get("HIFY_WORKSPACE_ROOT") or os.getcwd(),
    )
