# 072 Customer Assistant Live ReAct Acceptance

## Goal

Add a dedicated opt-in live gate named
`customer-assistant-live-react-acceptance`.

The gate must use OpenRouter or another OpenAI-compatible provider and the model
pool:

- `xiaomi/mimo-v2-flash`
- `qwen/qwen3.5-9b`
- `deepseek/deepseek-v4-flash`

## Acceptance Criteria

- Default CI does not call live providers.
- The gate runs only when `HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE=1`.
- Live execution requires an OpenAI-compatible API key from `OPENROUTER_API_KEY`
  or `HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY`.
- The provider base URL defaults to `https://openrouter.ai/api/v1`, with
  `OPENROUTER_BASE_URL` or `HIFY_CUSTOMER_ASSISTANT_LIVE_BASE_URL` override.
- Evidence is written under
  `artifacts/slices/072-customer-assistant-live-react-acceptance/`.
- Artifact output records models, category verdicts, and attempts, but never
  records API keys, tokens, or secrets.
- Coverage includes:
  - main runtime task-recognition accuracy;
  - Two-Stage recommendation quality;
  - ReAct worker true tool calls, high-risk write blocking, and event echo.

## Evidence

- RED:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/red.txt`
- Unit:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/unit.txt`
- Acceptance default skip:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/acceptance-skip.txt`
- Live artifact:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/live/customer-assistant-live-react-acceptance.md`
- OpenRouter DeepSeek verification:
  `artifacts/slices/072-customer-assistant-live-react-acceptance/live/openrouter-deepseek-v4-flash-run.txt`

## Latest Live Verification

- Date: 2026-06-17
- Provider: OpenRouter OpenAI-compatible API
- Model pool override: `deepseek/deepseek-v4-flash`
- Database: disposable MySQL8 database
- Result: acceptance passed, 1 test passed, 6 live model calls, all required
  categories completed.
- Redaction: live artifact records provider/model/category evidence and does
  not record API keys.
