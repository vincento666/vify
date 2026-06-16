# Plan 089

## 089.1 Fallback Attempt Debug Payload

- Add RED unit coverage for a primary provider failure followed by a fallback
  model success.
- Store sanitized fallback attempt metadata in the existing LLM debug payload.
- Keep effective model and usage projection accurate after fallback.

## Gates

- RED unit failure before implementation.
- Green focused workflow LLM completer tests.
- Green selected workflow node-run integration tests.
- Ruff for touched backend/test files.
