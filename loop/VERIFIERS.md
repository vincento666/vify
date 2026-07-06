# Loop Verifiers

These commands verify `222.11 Live LLM Real-Case UAT`.

They are operational loop checks. Spec source remains `specs/222-*`.

## Preflight

```bash
/opt/homebrew/bin/rtk uv run python - <<'PY'
from pathlib import Path
import os
import re

names = [
    "OPENROUTER_API_KEY",
    "OPENROUTER_BASE_URL",
    "OPENROUTER_MODEL",
    "AI_ASSISTANT_LIVE_LLM",
    "HIFY_AI_ASSISTANT_LIVE_LLM",
    "HIFY_RUN_LIVE_AI_ASSISTANT",
    "HIFY_AI_ASSISTANT_LIVE_BUDGET_USD",
    "AI_ASSISTANT_OPENROUTER_API_KEY",
    "AI_ASSISTANT_OPENROUTER_API_KEY_ENV",
    "AI_ASSISTANT_OPENROUTER_MODEL",
    "AI_ASSISTANT_OPENROUTER_BASE_URL",
]

def state(value: str) -> str:
    return "set" if value else "missing"

print("process_env:")
for name in names:
    print(f"{name}={state(os.environ.get(name, ''))}")

for path in [Path(".env"), Path(".env.local"), Path(".env.test")]:
    if not path.exists():
        continue
    text = path.read_text(errors="ignore")
    print(f"\n{path}:")
    for name in names:
        match = re.search(r"^\s*" + re.escape(name) + r"\s*=\s*(.+)$", text, re.M)
        print(f"{name}={state(match.group(1).strip() if match else '')}")
PY
```

If `OPENROUTER_API_KEY` or the confirmed AI Assistant live-provider key ref is
missing from the current process, the live verifier must read it as a
runtime-only secret. It must not be written to `.env`, artifacts, or logs.

## RED After Human Gate

These are blocked until provider/model/key/budget and realistic-case prompts
are confirmed.

```bash
/opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py -q
```

Expected RED artifacts after the human gate:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/red-live-llm.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/red-live-realistic-cases.txt
```

## Green After Human Gate

```bash
/opt/homebrew/bin/rtk uv run pytest tests/unit/ai_assistant/test_qwen_live_planner.py tests/unit/ai_assistant/test_business_adapter.py -q
/opt/homebrew/bin/rtk uv run pytest tests/contract/test_ai_assistant_live_qwen_api.py tests/contract/test_ai_assistant_tool_runtime_api.py -q
/opt/homebrew/bin/rtk uv run pytest tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py -q
/opt/homebrew/bin/rtk uv run ruff check app/modules/ai_assistant tests/unit/ai_assistant/test_qwen_live_planner.py tests/unit/ai_assistant/test_business_adapter.py tests/contract/test_ai_assistant_live_qwen_api.py tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py
/opt/homebrew/bin/rtk uv run python -m compileall -q app/modules/ai_assistant tests/unit/ai_assistant tests/contract/test_ai_assistant_live_qwen_api.py tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py
/opt/homebrew/bin/rtk git diff --check -- app/modules/ai_assistant tests/unit/ai_assistant tests/contract/test_ai_assistant_live_qwen_api.py tests/e2e/test_ai_assistant_live_qwen_openrouter_e2e.py specs/222-ai-assistant-general-harness-mvp loop
```

Live provider target:

```text
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=qwen/qwen3.6-27b
```

## Real-Case UAT After Human Gate

Required artifacts:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/live-llm-uat.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/live-realistic-cases-uat.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/screenshots/
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/audit-export-redacted.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/reviewer-round1.md
```
