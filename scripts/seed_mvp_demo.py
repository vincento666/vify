from __future__ import annotations

import os
from pathlib import Path

from app.core.database import get_session_factory, initialise_database
from app.modules.demo.mvp_seed import seed_mvp_demo, verify_mvp_demo_topology, write_mvp_demo_env


def main() -> None:
    initialise_database()
    env_path = Path(os.getenv("HIFY_MVP_DEMO_ENV_PATH", ".env"))
    with get_session_factory()() as session:
        result = seed_mvp_demo(session)
        write_mvp_demo_env(env_path, result)
        report = verify_mvp_demo_topology(session, env_text=env_path.read_text(encoding="utf-8"))
    if not report["ok"]:
        failed = ", ".join(check["name"] for check in report["checks"] if check["status"] != "passed")
        raise RuntimeError(f"MVP demo topology verification failed: {failed}")
    print("Seeded Hify MVP demo topology:")
    print(f"- Chatflow SOP bindings: {len(result.chatflow_bindings)}")
    print(f"- Customer assistant sessions: {','.join(str(item) for item in result.customer_session_ids)}")
    print(f"- Knowledge bases: {','.join(str(item) for item in result.knowledge_base_ids)}")
    print(f"- Demo stories: {','.join(result.story_ids)}")
    print("- Verification: passed")
    print(f"- Story coverage: {report['storyCoverage']['covered']}/{report['storyCoverage']['required']}")
    print("No API keys were written; keep live provider credentials in shell env or provider config.")


if __name__ == "__main__":
    main()
