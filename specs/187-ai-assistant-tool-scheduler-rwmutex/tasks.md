# Tasks 187: AI Assistant Tool Scheduler RWMutex

## 187.0 Documentation Sign-Off

- [x] Create `187-ai-assistant-tool-scheduler-rwmutex`.
- [x] Record that 184 originally named scheduler as 185, while committed spec
      185 is now `185-mysql8-runtime-unit-harness-hardening`.
- [x] Record that 186 has no directory in this checkout but is semantically
      reserved by the 184 roadmap for prompt/skills/memory/compaction.
- [x] Limit this spec to PRD Phase 4 scheduler/RWMutex work.
- [x] Declare backend-first scope with no frontend visual changes.
- [x] Declare MySQL8-only persistence and test evidence.
- [x] Declare real LLM tests deferred, with optional future OpenRouter probes
      environment-gated only.
- [x] Save planning evidence under
      `artifacts/slices/187-ai-assistant-tool-scheduler-rwmutex/187.0/`.

## 187.1 Scheduler And RWMutex Backend Slice

- [x] RED: unit tests fail for read-only compatible calls sharing a parallel
      batch.
- [x] RED: unit tests fail for write calls serializing against overlapping
      read/write resource keys.
- [x] RED: unit tests fail for unresolved resource templates falling back to a
      conservative serial lock.
- [x] RED: MySQL8 integration and contract tests fail for persisted
      scheduler/resource-lock metadata on tool-call rows and event payloads.
- [x] RED: contract/E2E tests fail for scheduler metadata exposed through AI
      Assistant run/event/result/inspector payloads.
- [x] Implement resource template resolution for tool manifests.
- [x] Implement scheduler plan metadata:
      `scheduler_batch_id`, `scheduler_position`, `lock_mode`,
      `read_resource_keys`, `write_resource_keys`, `resource_lock_reason`, and
      `parallel_eligible`.
- [x] Implement resource-keyed RWMutex decision logic.
- [x] Execute compatible read-only tool calls in bounded parallel batches.
- [x] Serialize write tool calls in planned order when resources overlap.
- [x] Preserve 184 approval/proposed-action behavior for business writes.
- [x] Persist scheduler metadata in MySQL8-backed repository paths.
- [x] Emit scheduler events and include scheduler metadata in tool events.
- [x] Prove event replay remains monotonic and deterministic per run.
- [x] Run focused scheduler unit, integration, contract, and E2E gates.
- [x] Save evidence under
      `artifacts/slices/187-ai-assistant-tool-scheduler-rwmutex/187.1/`.

## 187.2 Aggregate Backend Acceptance

- [ ] Rerun 187.1 focused gates.
- [ ] Rerun relevant 184 AI Assistant backend regressions for kernel, security,
      inspector, and event replay.
- [ ] Run MySQL8 boundary or focused SQLite scan for new scheduler tests.
- [ ] Run lint/type gates used by the existing AI Assistant backend.
- [ ] Confirm no frontend visual files changed.
- [ ] Record that browser UAT and remScaleClosure are not applicable because
      this backend-first slice does not alter frontend visuals.
- [ ] Save final evidence under
      `artifacts/slices/187-ai-assistant-tool-scheduler-rwmutex/187.2/`.
- [ ] Update this task list only after evidence exists.
