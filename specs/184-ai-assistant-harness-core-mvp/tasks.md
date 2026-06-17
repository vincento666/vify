# Tasks 184: AI Assistant Harness Core MVP

## 184.0 Spec Sign-Off

- [x] Confirm latest visible spec id is
      `183-final-openrouter-live-gate-revalidation`.
- [x] Create `184-ai-assistant-harness-core-mvp`.
- [x] Limit this spec to PRD Phase 0 through Phase 3.
- [x] Defer PRD Phase 4 through Phase 7 to follow-up specs 185 through 188.
- [x] Save documentation evidence under
      `artifacts/slices/184-ai-assistant-harness-core-mvp/184.0/`.

## 184.1 Phase 0 Minimal Harness Kernel

- [x] RED: repository/domain/API tests fail for session, run, message, event,
      tool-call persistence, read-only Tool Registry, and event replay.
- [x] Implement `app/modules/ai_assistant` domain models for session, run,
      message, event, tool call, tool manifest, and harness result.
- [x] Implement persistence repository and SQLAlchemy schema.
- [x] Implement monotonically increasing event sequence per run.
- [x] Implement minimal Prompt Assembler.
- [x] Implement read-only Tool Registry with deterministic `echo_context`.
- [x] Implement one-turn harness loop:
      `reason -> validate -> act -> observe -> final`.
- [x] Add `/api/v1/ai-assistant/...` Phase 0 endpoints.
- [x] Preserve `{code, message, data}` response envelope.
- [x] Prove one message can produce a final answer and replayed event history.
- [x] Save RED/unit/integration/contract/E2E evidence under
      `artifacts/slices/184-ai-assistant-harness-core-mvp/184.1/`.

## 184.2 Phase 1 Sandbox And Approval Boundary

- [x] RED: permission/sandbox/approval tests fail for read-only allow,
      high-risk approval-required, denied no-execute, approved audit, and
      sandbox-denied behavior.
- [x] Implement risk classifier and approval modes.
- [x] Implement Sandbox Policy.
- [x] Implement Permission Middleware.
- [x] Persist approval records and proposed actions.
- [x] Add approve/deny API endpoints.
- [x] Emit `approval.required`, `approval.granted`, `approval.denied`,
      `sandbox.denied`, and `proposed_action.created` events.
- [x] Prove high-risk business mutations become proposed actions unless
      explicitly pre-approved.
- [x] Save RED/unit/integration/contract/E2E evidence under
      `artifacts/slices/184-ai-assistant-harness-core-mvp/184.2/`.

## 184.3 Phase 2 Conversation Execution Echo

- [x] RED: frontend tests fail for event-card rendering and refresh recovery.
- [x] Add frontend AI Assistant API client.
- [x] Add center conversation timeline.
- [x] Render orchestration phase, model-call summary, tool-call, approval,
      sandbox, proposed-action, error, and run result cards.
- [x] Reload persisted events after refresh.
- [x] Keep hidden reasoning out of the UI.
- [x] Run backend event-envelope contract regression.
- [x] Run frontend unit tests and `remScaleClosure`.
- [x] Run browser UAT and save screenshot/notes.
- [x] Save evidence under
      `artifacts/slices/184-ai-assistant-harness-core-mvp/184.3/`.

## 184.4 Phase 3 Conversation List And Right Inspector

- [x] RED: frontend tests fail for session list, active run inspector,
      approval queue, right-panel tool calls, recent errors, and refresh
      behavior.
- [x] Add left conversation/session list.
- [x] Add create/select conversation workflow.
- [x] Add right run/task inspector.
- [x] Show active run status, tasks, tool calls, approvals, recent errors,
      elapsed time, token placeholders, and event timeline.
- [x] Add approve/deny controls from the UI.
- [x] Add or update inspector API contract test.
- [x] Run frontend unit tests and `remScaleClosure`.
- [x] Run product-shell E2E and browser UAT with screenshots.
- [x] Save evidence under
      `artifacts/slices/184-ai-assistant-harness-core-mvp/184.4/`.

## 184.5 Final Aggregate Acceptance

- [x] Merge subagent reports and resolve cross-slice conflicts.
- [x] Rerun focused slice gates.
- [x] Run aggregate backend unit, RED, integration, contract, and E2E gates.
- [x] Run full frontend unit and `remScaleClosure`.
- [x] Run browser UAT for AI Assistant shell.
- [x] Save final evidence and screenshots under
      `artifacts/slices/184-ai-assistant-harness-core-mvp/184.5/`.
- [x] Record final residual risk list.
- [x] Mark the goal complete only after evidence and UAT are complete.

## Later Specs

- [ ] 185: tool scheduler and RWMutex.
- [ ] 186: prompt, skills, memory, and compaction.
- [ ] 187: customer-assistant subagent bridge.
- [ ] 188: observability, benchmark, replay, and governance.
