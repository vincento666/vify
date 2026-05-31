# Plan 003: Provider Management

## Architecture

- `app/modules/provider/web/router.py`
- `app/modules/provider/web/schemas.py`
- `app/modules/provider/domain/service.py`
- `app/modules/provider/infra/orm.py`
- `app/modules/provider/infra/repository.py`
- `app/modules/provider/infra/llm_adapters.py`

## Testing Notes

- Use fake HTTP servers/fixtures for provider APIs.
- Do not call real OpenAI/Anthropic/Ollama in tests.
- Provider health task must be callable deterministically by tests; real
  scheduling is configured separately.

## Slice Order

003.1 -> 003.2 -> 003.3 -> 003.4 -> 003.5
