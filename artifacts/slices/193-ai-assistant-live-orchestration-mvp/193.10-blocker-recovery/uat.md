# 193.10 Blocker Recovery UAT

Date: 2026-06-18

Scope:
- Real OpenRouter `qwen/qwen3.5-27b` AI Assistant browser journey.
- Tool planning, tool execution, write approval, approval execution, stream
  output assembly, usage metrics, one-screen shell, and cleanup controls.

Resolved blockers:
- MySQL8 integration/contract/e2e needed an admin URL so disposable databases
  could receive full privileges for indexes and DML.
- OpenRouter model id `qwen/qwen3.5-27b` was verified from `/models`; the
  previously observed 401 was not reproduced after controlled request setup.
- Qwen reasoning-only payloads now feed thought summary and do not create
  duplicate visible model output.
- OpenRouter SSE `delta.reasoning` is preserved separately from visible content
  deltas.
- Model config panel closes on send and no longer blocks approval controls.
- Approval buttons disappear once the matched approval leaves pending state.

Gate evidence:
- Backend focused unit/contract:
  `rtk uv run pytest tests/unit/ai_assistant tests/unit/chat/test_llm_request_client.py tests/contract/test_ai_assistant_live_stream_api.py`
  -> 22 passed.
- MySQL8 integration/contract/e2e with admin URL:
  `mysql-admin-gate-final.txt` -> 6 passed.
- Frontend rem + AI Assistant focused unit:
  `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantShell.test.ts src/remScaleClosure.test.ts`
  -> 17 passed.
- Full frontend unit:
  `rtk npm --prefix frontend run test:unit` -> 96 files / 397 tests passed.
- Frontend build:
  `rtk npm --prefix frontend run build` -> passed.
- Deterministic browser E2E:
  `deterministic-shell-e2e-final.txt` -> PASS.
- Real qwen browser E2E:
  `real-qwen-shell-e2e-final-2.txt` -> PASS.

Screenshots:
- `screenshots/ai-assistant-real-qwen-before-cleanup-final.png`
- `screenshots/ai-assistant-real-qwen-after-cleanup-final.png`
- `screenshots/ai-assistant-deterministic-before-cleanup-final.png`
- `screenshots/ai-assistant-deterministic-after-cleanup-final.png`

Residual risk:
- The in-app browser bridge did not expose an attachable tab in this run, so
  the browser UAT was executed through Playwright against the same local app URL.
- OpenRouter model behavior can vary; tests now cover protocol handling and
  the UAT uses a real qwen run, but future model-side tool-call drift remains
  possible.
