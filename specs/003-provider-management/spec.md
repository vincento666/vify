# Spec 003: Provider Management

## Goal

Replicate the current model provider management feature: provider CRUD,
model config lookup, provider health state, connection test, and LLM adapter
contract.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 003.1 Provider CRUD | User can create, list, update, delete/toggle providers | RED: API contract fails; Unit: schema validation; Integration: DB CRUD; E2E: provider page smoke; UAT: create/edit/delete provider |
| 003.2 Model config contract | Agent can validate enabled model configs | RED: disabled model test fails; Unit: repository filters; Integration: model lookup; E2E: provider detail models; UAT: model shown in UI |
| 003.3 Connection test | User can test provider connectivity and see latency/errors | RED: mocked httpx test fails; Unit: error mapping; Integration: `/test-connection`; E2E: button flow; UAT: success/failure message |
| 003.4 Provider health task | Enabled providers get health state updates | RED: scheduled task behavior test fails; Unit: state transition; Integration: DB update; E2E: provider health visible; UAT: health badge changes |
| 003.5 LLM adapter contract | OpenAI/Anthropic/Ollama adapter parses sync and stream responses | RED: parser fixtures fail; Unit: stream parser; Integration: fake HTTP server; E2E: N/A; UAT: dev note with fixture proof |

## Compatibility Rules

- Provider types preserve current strings: `OPENAI`, `ANTHROPIC`, `OLLAMA`,
  `AZURE_OPENAI`, `OPENAI_COMPATIBLE`, `DEEPSEEK`.
- Auth config remains JSON-compatible.
- Connection test returns current frontend-compatible shape.
