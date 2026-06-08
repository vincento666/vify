## 099 workflow/chatflow final lifecycle gate

Date: 2026-06-09

### Scope

- Workflow canvas UX lifecycle.
- Workflow publish.
- Chatflow conversation run.
- Chatflow trial chat panel.
- Chatflow publish.
- Edge insert button hover/selection visibility regressions.

### Changes

- `workflow-canvas-ux-lifecycle.mjs` no longer depends on live LLM providers for routing/lifecycle assertions.
- The multi-condition workflow and chatflow guide-question branch use a local deterministic API server.
- Dedicated LLM behavior remains covered by the existing LLM/run scripts; this gate focuses on lifecycle continuity.

### Fresh gates

- `e2e-workflow-canvas-ux-lifecycle.txt`: passed.
- `e2e-workflow-publish.txt`: passed.
- `e2e-chatflow-conversation-run.txt`: passed.
- `e2e-chatflow-trial-chat-panel.txt`: passed.
- `e2e-chatflow-publish.txt`: passed.
- `e2e-workflow-edge-insert-hover-only-rerun.txt`: passed.
- `e2e-chatflow-edge-insert-visibility-rerun.txt`: passed.
- `e2e-chatflow-edge-interactions-rerun.txt`: passed.
- `full-unit.txt`: passed.
- `build.txt`: passed.
