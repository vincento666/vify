# Customer Assistant AI Workbench Redesign Subagent Reports

Date: 2026-06-20

## Slice A - UI Contract And ViewModel RED Tests

Agent: Epicurus

- 修改范围: `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`,
  `frontend/src/views/customerAssistant/customerAssistantViewModel.test.ts`
- 红测证据: `slice-a-red.txt`, later consolidated into `slice-1-red.txt`
- 实现摘要: added business-first right-workbench UI contract expectations and
  explicit no-source fallback coverage for operator Q&A.
- 已跑门禁: red contract run before implementation; later green runs are
  `slice-1-panel-merge.txt` and `slice-1-focused-green.txt`.
- 剩余风险: initial 3-tab naming conflicted with final 5-tab IA and was merged
  by the main agent.

## Slice B - Right Workbench UI Implementation

Agent: Volta, integrated by main agent

- 修改范围: `frontend/src/views/customerAssistant/CustomerAssistantPanel.vue`,
  `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`
- 红测证据: `slice-1-panel-merge.txt` failed before the final 5-tab merge.
- 实现摘要: delivered the final `聚焦 / AI助手 / 办理 / 证据 / 配置` right workbench,
  default focus cards, assistant Q&A/event pane, synchronized confirmation
  cards, and separated configuration tab.
- 已跑门禁: panel contract, focused frontend tests, full frontend unit,
  remScaleClosure, frontend build, browser UAT.
- 剩余风险: real local in-app page depends on seeded demo data; empty local DB
  shows an empty session state while preserving layout.

## Slice C - Runtime And API Bridge Boundary Review

Agent: Huygens

- 修改范围: read-only architecture review, no direct file edits.
- 红测证据: not applicable because this was a read-only boundary slice.
- 实现摘要: confirmed Slice 1 can reuse existing `operatorKnowledgeQa`,
  `proposedActions`, runtime events, and AI assistant bridge contracts.
- 已跑门禁: main agent ran backend unit, integration, and contract gates after
  integration.
- 剩余风险: a richer dedicated customer-assistant Copilot harness remains a later
  product slice.

## Slice D - Browser UAT Evidence

Agent: Kierkegaard, updated by main agent

- 修改范围: `frontend/e2e/customer-assistant-final-uat-checkpoints.mjs`,
  `docs/customer-assistant-uat-checklist.md`
- 红测证据: first UAT run failed on a strict Playwright text locator and was
  corrected without changing product behavior.
- 实现摘要: verifies one-screen three-column layout, default `聚焦`, AI assistant
  Q&A, config progressive disclosure, focus confirmation, assistant sync,
  business task update, evidence audit update, and screenshot capture.
- 已跑门禁: `slice-1-browser-uat.txt`,
  `slice-1-real-stack-layout-smoke.txt`, in-app browser smoke.
- 剩余风险: final UAT script uses route mocks for deterministic business data;
  real-stack smoke verifies layout against the running local FastAPI/Vite stack.

## Main Agent Integration

- 修改范围: merged UI contract, implementation, docs, UAT, and a narrow backend
  task-control flush/readback fix in
  `app/modules/customer_assistant/domain/service.py`.
- 红测证据: `slice-1-red.txt`,
  `slice-1-backend-integration-retry-single.txt` before fix.
- 实现摘要: resolved tab IA conflicts, moved technical evidence out of default
  view, kept passenger conversation separate from AI assistant Q&A, synchronized
  confirmation state across tabs, and restored confirmed retry worker readback.
- 已跑门禁: backend unit/integration/contract; frontend full unit, focused unit,
  remScaleClosure, build; browser UAT; real-stack smoke; in-app browser smoke.
- 剩余风险: full real demo content requires local seed data.
