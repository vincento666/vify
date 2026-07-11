# Tasks 188: AI Assistant Workspace MEMORY.md

## Historical Completed Work

- [x] 188.0 documentation sign-off.
- [x] 188.1 domain prompt tracer: prompt layers, read-only skills, memory-item
  rendering, and compaction-summary layer.
- [x] 188.3 historical aggregate acceptance, limited to behavior implemented at
  that time.

## Superseded Work — Not Implemented

188.2 JSON working-memory and deterministic-compaction persistence is cancelled
by the accepted MEMORY.md-only contract. These are historical requirements, not
open tasks:

- persist durable memory in context_json or a memory DB table;
- make deterministic compaction summary a second durable memory source;
- feed legacy aiAssistantMemory into future prompt memory.

## Contract Revision

- [x] Freeze one MEMORY.md per trusted user/workspace scope.
- [x] Freeze 30-day heading-based bounded reader; no fixed tail-N read.
- [x] Freeze full-day 100-token cap.
- [x] Freeze model extraction every three unprocessed COMPLETED runs across
  sessions.
- [x] Freeze cursor DB as operational metadata only.
- [x] Freeze daily scheduler and Spec 189 as out of scope.
- [x] Freeze Spec 190 to token/cost only.

## 188.4 Scope Isolation And Markdown Store

- [x] TDD preflight and observable RED.
- [x] Resolve trusted user/workspace scope; reject arbitrary paths and escape.
- [x] Create one canonical MEMORY.md per scope.
- [x] Locate rolling 30-day start line from strict date headings.
- [x] Read only bounded content from calculated line through EOF.
- [x] Merge/dedupe/compress today's block to at most 100 tokens.
- [x] Add per-scope lock and atomic replacement.
- [x] Cover malformed/future headings, concurrency, and isolation.
- [x] Save evidence and pass Checker/Reviewer under
  artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.4/.

## 188.5 Session Scope And Prompt Cutover

- [ ] TDD preflight and observable RED.
- [ ] Persist and enforce user/workspace scope for sessions and runs.
- [ ] Inject own rolling MEMORY.md into working-memory prompt layer.
- [ ] Stop legacy JSON memory writes and prompt reads.
- [ ] Preserve required public memory fields as MEMORY.md-derived read-only
  projections.
- [ ] Add MySQL8 contract and backend E2E isolation/reload proof.
- [ ] Run kernel, security, inspector, event, scheduler, and ToolRunner
  regressions.
- [ ] Save evidence and pass Checker/Reviewer.

## 188.6 Three-Successful-Run Extraction

- [ ] TDD preflight and observable RED.
- [ ] Persist per-scope successful-run counter and extraction cursor.
- [ ] Count only new COMPLETED runs across sessions.
- [ ] Trigger configured model extractor for each next batch of three.
- [ ] Merge result into today's capped block.
- [ ] Advance cursor only after atomic file success.
- [ ] Retry model/write failures without duplicate or lost batches.
- [ ] Recover idempotently across pre-write, post-write, and pre-cursor-commit
  crash windows using batch/input/target hashes.
- [ ] Leave trailing one or two runs pending.
- [ ] Save MySQL8/E2E evidence and pass Checker/Reviewer.

## 188.7 Aggregate Acceptance

- [ ] Rerun all 188.4-188.6 required gates.
- [ ] Prove DB stores no memory text.
- [ ] Prove no fixed tail-N read and no new aiAssistantMemory writes.
- [ ] Confirm frontend visual, customer-assistant, daily scheduler, and Spec 189
  boundaries.
- [ ] Save final evidence, Checker report, Reviewer report, and residual risks.
