from __future__ import annotations


AI_ASSISTANT_RUNTIME_JOB_TYPE = "ai_assistant_run"


def ai_assistant_runtime_job_payload(run_id: int) -> dict[str, str]:
    return {"runRef": f"ai-assistant-run:{int(run_id)}"}
