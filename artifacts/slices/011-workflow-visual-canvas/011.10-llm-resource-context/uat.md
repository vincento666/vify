# 011.10 Browser UAT

Date: 2026-06-02

## Coze Reference

- Live Coze reference URL was attempted earlier in this sequence, but the in-app browser automation layer timed out on the Coze page and reset the browser session.
- Alignment target for this slice remains the recorded Coze LLM panel/resource behavior in `specs/011-workflow-visual-canvas/spec.md`: LLM `技能` area is a resource selector, Knowledge is currently callable, MCP tools and subworkflows are visibly not runnable until their node-level runtime exists.

## Local Browser UAT

Local URL used: `http://127.0.0.1:15182/workflows/558/canvas`

Validated in the Codex in-app browser:

- Opened a workflow containing `开始 -> 大模型 -> 结束`.
- Selected the LLM node and verified the `技能` section shows a persisted Knowledge resource.
- Opened the resource picker and verified:
  - `知识库检索` is visible as runnable and says it injects LLM context.
  - `MCP 工具` is visible but marked `当前不可运行`.
  - `子工作流` is visible but marked `当前不可运行`.
- Ran the workflow through the browser test panel using the live default LLM provider.
- The LLM returned the exact knowledge-base token `KB_CONDITION_KC_1780317732926` after the Knowledge resource context was prepended to the model prompt.

## Evidence

- `red.txt`: RED failures showed resources were ignored and unsupported MCP resources were not rejected.
- `unit.txt`: backend resource-context and guard tests passed.
- `integration.txt`: API-level resource-context and guard tests passed.
- `frontend-unit.txt`: frontend workflow unit tests passed.
- `frontend-build.txt`: production frontend build passed.
- `e2e.txt`: frontend resource UI E2E passed.
- Screenshots:
  - `screenshots/e2e-llm-resources.png`
  - `screenshots/browser-uat-resource-panel-after-context-order.png`
  - `screenshots/browser-uat-resource-picker.png`
  - `screenshots/browser-uat-resource-exact3-run.png`

## Verdict

Pass. Knowledge resources now execute as LLM context; MCP Tool and Subworkflow resources are explicitly guarded instead of silently ignored.
