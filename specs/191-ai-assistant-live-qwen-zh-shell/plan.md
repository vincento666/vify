# Plan 191: AI Assistant Live Qwen Chinese Shell

## Slice 191.0 Documentation Sign-Off

- Create this spec, plan, and task list.
- Record that OpenRouter model id was verified as `qwen/qwen3.5-27b`.
- Record that API keys must stay out of repo artifacts.

## Slice 191.1 One-Screen Chinese Shell

Public interface: `/ai-assistant` frontend route.

TDD behavior:

- shell CSS constrains the workbench to the viewport instead of using a long
  page;
- left, center, and right columns own their vertical overflow;
- Chinese copy replaces visible English labels in the AI Assistant shell.

Implementation:

- adjust `AiAssistantShell.vue` layout sizing;
- use `rem` for visual dimensions;
- update shell unit contract and browser e2e selectors.

Gates:

- frontend shell unit;
- `remScaleClosure`;
- browser UAT.

## Slice 191.2 Qwen Live Planning Events

Public interface: `/api/v1/ai-assistant/sessions/{id}/messages`.

TDD behavior:

- default settings expose OpenRouter `qwen/qwen3.5-27b` without exposing keys;
- a fake live client can drive model tool-call decisions through the harness;
- visible Chinese events show model planning, thought summary, stream chunks,
  selected tools, file operation intent, skill intent, and task-panel
  orchestration;
- standard tests remain deterministic without live credentials.

Implementation:

- add AI Assistant LLM settings to `app.core.config.Settings`;
- add a small live planner that reuses the existing OpenAI-compatible request
  utilities;
- add `modelMode`/`model_mode` request support, defaulting to deterministic;
- route model-selected tool calls into the existing scheduler and tool
  registry.

Gates:

- focused backend unit;
- focused contract;
- AI Assistant integration/e2e regressions where practical;
- ruff and mypy for touched backend modules.

