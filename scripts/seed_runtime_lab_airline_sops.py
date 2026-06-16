from __future__ import annotations

import os
from pathlib import Path

from app.core.database import get_session_factory, initialise_database
from app.modules.runtime_lab.infra.airline_chatflow_seed import (
    DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL,
    DEFAULT_RUNTIME_LAB_BASE_URL,
    seed_runtime_lab_airline_chatflows,
    seed_runtime_lab_live_agent,
    write_runtime_lab_env,
)


def main() -> None:
    initialise_database()
    base_url = os.getenv("OPENROUTER_BASE_URL", DEFAULT_RUNTIME_LAB_BASE_URL).strip()
    model = os.getenv("OPENROUTER_MODEL", DEFAULT_RUNTIME_LAB_ARBITRATOR_MODEL).strip()
    api_key = (
        os.getenv("OPENROUTER_API_KEY")
        or os.getenv("HIFY_RUNTIME_LAB_INTENT_ARBITRATOR_API_KEY")
        or ""
    ).strip()
    with get_session_factory()() as session:
        bindings = seed_runtime_lab_airline_chatflows(session)
        agent_id = None
        if api_key:
            agent_id = seed_runtime_lab_live_agent(session, api_key=api_key, base_url=base_url, model=model)
    write_runtime_lab_env(
        Path(".env"),
        bindings=bindings,
        base_url=base_url,
        model=model,
        mode="llm" if api_key else "fake",
    )
    print("Seeded RuntimeLab airline Chatflow SOPs:")
    for sop_id, chatflow_id in bindings.items():
        print(f"- {sop_id}: {chatflow_id}")
    if agent_id is not None:
        print(f"Seeded live Chatflow LLM agent: {agent_id}")
    else:
        print("No OPENROUTER_API_KEY found; .env keeps fake arbitrator mode and no API key was written.")


if __name__ == "__main__":
    main()
