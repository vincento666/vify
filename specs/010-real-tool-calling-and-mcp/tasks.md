# Tasks 010: Real Tool Calling And MCP

## 010.1 Tool schema serialization

- [x] RED: tools request fixture tests fail.
- [x] Implement serializer.
- [x] Gates pass.

## 010.2 Tool-call parsing

- [x] RED: tool_calls response fixture tests fail.
- [x] Implement parser.
- [x] Gates pass.

## 010.3 MCP execution

- [x] RED: fake MCP execution tests fail.
- [x] Implement real MCP runner.
- [x] Gates pass.

## 010.4 Second LLM round

- [x] RED: two-round orchestration test fails.
- [x] Implement second-round flow.
- [x] Gates pass.

## 010.5 Production hardening

- [x] RED: timeout/failure tests fail.
- [x] Implement timeout, metrics, audit logs.
- [x] Gates pass.

## 010.6 Live provider acceptance

- [x] RED: live OpenRouter acceptance is skipped unless explicitly enabled.
- [x] Run OpenRouter chat acceptance with `xiaomi/mimo-v2-flash`.
- [x] Run OpenRouter tool-call and second-round acceptance.
- [x] Record UAT artifact without API key material.
