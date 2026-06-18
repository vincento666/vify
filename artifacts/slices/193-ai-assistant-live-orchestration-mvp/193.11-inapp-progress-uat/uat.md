# 193.11 AI Assistant Complex Progress UAT

## Scope

- URL: `http://127.0.0.1:5173/ai-assistant`
- Model: OpenRouter `qwen/qwen3.5-27b`
- Task path: `read_workspace_file(specs/README.md)` -> `search_knowledge_base` -> `invoke_skill(tdd)` -> `write_workspace_file(tmp/ai-assistant-uat-progress.md)` with approval -> final answer.

## Final UAT

Command:

```bash
HIFY_AI_ASSISTANT_OPENROUTER_API_KEY=... rtk node frontend/e2e/ai-assistant-complex-progress-uat.mjs
```

Evidence:

- `complex-progress-real-qwen-green-5.txt`
- `complex-progress-uat.json`
- `screenshots/progress-running-early.png`
- `screenshots/progress-before-approval.png`
- `screenshots/progress-completed.png`

Final summary:

```json
{
  "sampleCount": 37,
  "sawTaskRows": true,
  "sawRunningTask": true,
  "sawAnimatedRunningTask": true,
  "sawStepSpinner": true,
  "finalHeader": "已处理44 条事件 / 4 次工具",
  "finalSteps": 14,
  "finalToolRows": 4,
  "finalAnswers": 1,
  "pageOverflowY": 0
}
```

## Gates

- Focused UI contract: `rtk npm --prefix frontend run test:unit -- src/views/aiAssistant/aiAssistantShell.test.ts` -> 16 passed.
- Frontend rem: `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` -> 1 passed.
- Full frontend unit: `rtk npm --prefix frontend run test:unit` -> 96 files / 400 tests passed.
- Frontend build: `rtk npm --prefix frontend run build` -> passed.
- AI Assistant backend unit/contract with MySQL8 admin DSN:
  `HIFY_MYSQL8_TEST_DATABASE_URL=... HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=... rtk uv run pytest tests/unit/ai_assistant ... -q` -> 28 passed.

## Remaining Risk

- Codex in-app browser bridge still returns: `Timed out waiting for the Browser webview to attach for this browser-use page`.
- The same local URL and flow pass in real Playwright Chromium. This leaves the in-app browser bridge as an environment/tooling blocker, not an AI Assistant product regression.
