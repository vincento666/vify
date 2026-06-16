from __future__ import annotations

import os
from pathlib import Path

from app.core.database import get_session_factory, initialise_database
from app.modules.demo.mvp_seed import seed_one_click_mvp_demo


def main() -> None:
    initialise_database()
    env_path = Path(os.getenv("HIFY_ONE_CLICK_DEMO_ENV_PATH", ".env.demo"))
    report_path = Path(
        os.getenv(
            "HIFY_ONE_CLICK_DEMO_REPORT_PATH",
            "artifacts/demo/one-click-mvp-demo-seed-report.json",
        )
    )
    with get_session_factory()() as session:
        result = seed_one_click_mvp_demo(session, env_path=env_path, report_path=report_path)
    if not result.report["ok"]:
        failed = ", ".join(
            check["name"] for check in result.report["checks"] if check["status"] != "passed"
        )
        raise RuntimeError(f"One-click MVP demo verification failed: {failed}")
    print("Seeded Hify one-click MVP demo:")
    print(f"- Env file: {env_path}")
    print(f"- Report: {report_path}")
    print(f"- Provider/model configs: {','.join(str(item) for item in result.seed.model_config_ids or [])}")
    print(f"- Chatflow SOP bindings: {len(result.seed.chatflow_bindings)}")
    print(f"- Customer assistant sessions: {','.join(str(item) for item in result.seed.customer_session_ids)}")
    print(f"- Knowledge bases: {','.join(str(item) for item in result.seed.knowledge_base_ids)}")
    print(f"- Demo stories: {','.join(result.seed.story_ids)}")
    print("- Verification: passed")
    print("No API keys were written; keep live provider credentials in shell env or provider config.")


if __name__ == "__main__":
    main()
