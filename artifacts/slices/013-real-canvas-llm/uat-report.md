# Spec013 Real Canvas LLM UAT

Date: 2026-06-01

## Scope

- Workflow canvas direct run with an LLM node must use the default real provider-backed Agent.
- Chatflow canvas direct run with an LLM node must use the default real provider-backed Agent.
- Neither path may return `LLM mock:` output.
- The test run panel must keep the structured result UI and avoid raw JSON code blocks.

## Local Provider

- Provider: OpenRouter-compatible OpenAI API
- Model: `xiaomi/mimo-v2-flash`
- Agent: `Canvas Live Agent`
- Secret values are stored only in local DB runtime configuration and are not recorded in this report.

## Gate Results

| Gate | Command / Method | Result |
| --- | --- | --- |
| Unit red/green | `uv run pytest tests/unit/workflow/test_service_provider_llm.py -q` | Passed, verifies provider-backed completer and no-live-agent rejection |
| Workflow unit suite | `uv run pytest tests/unit/workflow -q` | Passed, 12 tests |
| Python lint | `uv run ruff check app/modules/workflow/domain/service.py app/modules/workflow/web/router.py app/modules/agent/infra/repository.py tests/unit/workflow/test_service_provider_llm.py` | Passed |
| Python typing | `uv run mypy app/modules/workflow/domain/service.py app/modules/agent/infra/repository.py` | Passed |
| Frontend unit | `npm --prefix frontend run test:unit` | Passed, 18 files / 34 tests |
| API smoke: workflow | Create workflow + run LLM node via `/api/v1/workflows/{id}/runs` | Passed, token returned, no `LLM mock:` |
| API smoke: chatflow | Create chatflow + run LLM node via `/api/v1/chatflows/{id}/runs` | Passed, token returned, no `LLM mock:` |
| Browser e2e | `HIFY_E2E_BASE_URL=http://127.0.0.1:15182 node frontend/e2e/workflow-chatflow-llm-run.mjs` | Passed |

## Browser Evidence

- Workflow output token: `WORKFLOW_LIVE_*`
- Chatflow output token: `CHATFLOW_LIVE_*`
- Screenshots:
  - `artifacts/slices/013-real-canvas-llm/workflow-live.png`
  - `artifacts/slices/013-real-canvas-llm/chatflow-live.png`

The Codex in-app Browser control tool was not exposed in this session after tool discovery, so browser UAT was executed with Playwright against the same running local frontend and backend.
