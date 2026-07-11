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

- [x] TDD preflight and observable RED.
- [x] Persist and enforce user/workspace scope for sessions and runs.
- [x] Inject own rolling MEMORY.md into working-memory prompt layer.
- [x] Stop legacy JSON memory writes and prompt reads.
- [x] Preserve required public memory fields as MEMORY.md-derived read-only
  projections.
- [x] Add MySQL8 contract and backend E2E isolation/reload proof.
- [x] Run kernel, security, inspector, event, scheduler, and ToolRunner
  regressions.
- [x] Save evidence and pass Checker/Reviewer.

## 188.6 Three-Successful-Run Extraction

- [x] TDD preflight and observable RED.
- [x] Persist per-scope successful-run counter and extraction cursor.
- [x] Count only new COMPLETED runs across sessions.
- [x] Trigger configured model extractor for each next batch of three.
- [x] Merge result into today's capped block.
- [x] Advance cursor only after atomic file success.
- [x] Retry model/write failures without duplicate or lost batches.
- [x] Recover idempotently across pre-write, post-write, and pre-cursor-commit
  crash windows using batch/input/target hashes.
- [x] Leave trailing one or two runs pending.
- [x] Save MySQL8/E2E evidence and pass Checker/Reviewer.

## 188.7 Aggregate Acceptance

- [x] Rerun all 188.4-188.6 required gates.
- [x] Prove DB stores no memory text.
- [x] Prove no fixed tail-N read and no new aiAssistantMemory writes.
- [x] Confirm frontend visual, customer-assistant, daily scheduler, and Spec 189
  boundaries.
- [x] Save final evidence, Checker report, Reviewer report, and residual risks.
