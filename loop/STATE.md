# Loop State

## Current

- active spec: `specs/222-ai-assistant-general-harness-mvp/`
- frozen scope: `222.11 Live LLM Real-Case UAT`
- current checklist item: commit completed 222.11/222.12 slice work.
- current status: `222.11 complete; commit pending`
- human decision: option `A`, authorize a targeted reviewer-fix pass for
  `222.12`; after Reviewer round2 FAIL, human selected `A` again to continue
  with a narrow round3 fix; after Reviewer round3 FAIL, human selected `A`
  again to continue with a narrow approval-resume cancellation event fix.
- stop condition: quota/rate/provider error, repeated live UAT failure, leaked
  secret, or Checker/Reviewer evidence gap blocks `222.11`.
- next action: stage and commit completed slice work after final git scope
  review.
- runtime contract: OpenRouter `qwen/qwen3.6-27b` at
  `https://openrouter.ai/api/v1`; `OPENROUTER_API_KEY` is injected only into
  commands that need it and must not be written to files or logs.

## Goal Mode

Codex goal mode tracked the `222.12` targeted reviewer-fix pass. The
goal evidence is complete after targeted RED/green evidence, refreshed
self-gates, Browser UAT, Checker round4 PASS, and Reviewer round4 PASS were
recorded.
`222.11` resumed after the human provided an OpenRouter runtime key path and
confirmed live UAT should target `qwen/qwen3.6-27b`.

2026-07-06 update: the same human gate repeated across the original
Reviewer-round2 stop turn and two automatic goal continuations. The Codex goal
was marked `blocked` until a human explicitly chose the next action. Human
later selected option `A`; `222.12` is now complete after Checker round4 PASS
and Reviewer round4 PASS.

## Checklist

- [x] Read `AGENTS.md`.
- [x] Read universal loop protocol.
- [x] Read `loop/README.md`.
- [x] Read `specs/README.md`.
- [x] Read `docs/testing/acceptance-gates.md`.
- [x] Read active `spec.md`, `plan.md`, and `tasks.md`.
- [x] Complete `222.5 SessionRuntime` Checker and Reviewer gates.
- [x] Confirm next pending slice is `222.6 MemoryContext And ContextBudget`.
- [x] Freeze 222.6 scope in `loop/CURRENT.md`.
- [x] Update `loop/STATE.md` for 222.6.
- [x] Update `loop/VERIFIERS.md` for 222.6.
- [x] RED: unit tests fail for recursive AGENTS.md instruction memory and
      context-budget accounting.
- [x] RED: contract tests fail for session summary, working memory persistence,
      context-budget events, and inspector payload.
- [x] RED: E2E tests fail until context state survives refresh/reconnect.
- [x] RED: frontend tests fail until inspector context section renders usage,
      compaction, layer share, selected/dropped layers, and warning level.
- [x] Implement MemoryContext without `memory.md`, new dependency, or DB
      migration.
- [x] Implement ContextBudget and compaction snapshot accounting.
- [x] Emit context-budget events and expose inspector context payload.
- [x] Add approval-gated AGENTS.md update tool contract without unapproved
      real writes.
- [x] Run focused backend and frontend self gates.
- [x] Run Browser UAT with Codex in-app browser.
- [x] Run Checker verifiers round1.
- [x] Run Reviewer round1.
- [x] RED: reviewer round1 high findings reproduced for nested AGENTS.md and
      stale inspector memory.
- [x] Fix nested AGENTS.md run integration and inspector memory reload.
- [x] Fix selected/raw context usage and expose context audit references.
- [x] Refresh focused gates and Browser UAT after reviewer fixes.
- [x] Run Checker verifiers round2.
- [x] Run Reviewer round2.
- [x] Update `tasks.md`, artifacts, `loop/STATE.md`, and `loop/LESSONS.md`.
- [x] Human selected option `C`: run `222.7` Open Loop design/preflight only,
      no implementation.
- [x] Create `222.7-preflight` contract artifact.
- [x] Run Checker round1.
- [x] Run Reviewer round1.
- [x] Fix Reviewer round1 findings: fencing/current mismatch, non-objective
      lock contention, subjective shell/audit acceptance, missing start gate.
- [x] Run Checker round2.
- [x] Run Reviewer round2.
- [x] Human selected option `A`: authorize `222.7` implementation within the
      preflight contract, including permission/sandbox/DB-lock/schema changes.
- [x] RED: policy tests fail for missing session-level DSL dimensions.
- [x] RED: sandbox tests fail for missing session workspace, run temp,
      env/secret scope, cwd, network policy, resource limits, shell allowlist,
      and output redaction.
- [x] RED: lock tests fail for missing DB-backed READ/WRITE locks with lease,
      TTL, and fencing token.
- [x] Implement policy DSL.
- [x] Implement session sandbox.
- [x] Implement DB-backed resource locks.
- [x] Prove `always_approve` remains constrained by policy, sandbox, budget,
      and locks.
- [x] Run safety unit, integration, contract, E2E, Browser UAT, and docs gates.
- [x] Reviewer round1 FAIL reproduced as RED tests for node preload flags,
      sandbox env leakage, canonical path policy/lock bypass, concurrent DB
      lock acquisition, and budget rule enforcement.
- [x] Fix reviewer round1 findings.
- [x] Run Checker round2.
- [x] Run Reviewer round2.
- [x] Fix Reviewer round2 targeted mypy blocker.
- [x] Run Reviewer round3.
- [x] Human selected option `A`: authorize full `222.8 SkillRuntime`
      implementation after human gate.
- [x] RED: skill tests fail for missing directory discovery and metadata index.
- [x] RED: prompt tests fail until SKILL.md is loaded only after trigger match.
- [x] RED: audit tests fail for missing skill load and resource-read events.
- [x] Implement progressive skill discovery and loading.
- [x] Implement on-demand references/scripts/assets reads.
- [x] Add version/checksum/risk metadata to skill manifests.
- [x] Integrate `invoke_skill`, `read_skill_resource`, and `run_skill_script`
      with ToolRuntime, PermissionPolicy, ResourceLock events, and audit events.
- [x] Run 222.8 self-gates: unit, integration, contract, E2E, Browser UAT,
      ruff, py_compile, mypy-focused, and diff-check.
- [x] Update `spec.md`, `tasks.md`, and UAT artifact for 222.8.
- [x] Run Checker for 222.8 round1.
- [x] Run Checker for 222.8 round2.
- [x] Run Reviewer for 222.8.
- [x] Close 222.8 in spec/tasks/loop state.
- [x] Human selected option `A`: authorize full `222.9 TraceAuditEvalBudget`
      implementation within the confirmed audit/export boundary.
- [x] RED: trace tests fail for missing spans across run, model, tool,
      approval, stream, retry, fallback, skill, file edit, resource lock,
      context budget, and business adapter seam.
- [x] RED: audit export tests fail for missing prompt layer, context budget,
      compaction snapshot, plan, tool args/result, retry/fallback, approval,
      token/cost, file diff, adapter audit, and final result records.
- [x] Implement trace span model and export path.
- [x] Implement audit export.
- [x] Implement eval regression suite.
- [x] Implement token/cost budget and model degradation strategy.
- [x] Run trace/audit/eval/budget gates and docs gates.
- [x] Start `222.10 Aggregate Production Evaluation`.
- [x] RED: aggregate production eval fails for missing report module.
- [x] Implement initial aggregate production eval report module.
- [x] Run 222.10 self-gates: unit, contract, E2E, eval, frontend, rem, ruff,
      py_compile, focused mypy, diff-check, and Browser UAT.
- [x] Run Checker round1.
- [x] Run Reviewer round1.
- [x] Human selected option `A` for Reviewer round1 targeted fix.
- [x] Ground aggregate production eval in real artifacts and source assertions.
- [x] Generate `aggregate-trace-audit-export.json`.
- [x] Generate `aggregate-production-report.md` and JSON payload.
- [x] Update 222.10 docs gate.
- [x] Rerun 222.10 self-gates after reviewer-fix.
- [x] Run Checker round2.
- [x] Run Reviewer round2.

## Attempts

- 2026-07-06 `222.12` startup:
  - read `AGENTS.md`, `loop/README.md`, `loop/CURRENT.md`,
    `loop/VERIFIERS.md`, `docs/testing/acceptance-gates.md`, and active spec
    slice notes;
  - used `universal-work-loop` and `test-driven-development` skills;
  - froze the local implementation boundary to existing AI Assistant tables and
    current in-app browser UAT unless tests prove a human-gated architecture or
    schema change is unavoidable;
  - confirmed `222.11` live LLM gate remains waiting-human and must not be
    weakened by `222.12`.

- 2026-07-06 `222.12` stopped at Checker/Reviewer round1:
  - saved Checker FAIL:
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round1.md`;
  - saved Reviewer FAIL:
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round1.md`;
  - Browser UAT local deterministic path passed and saved evidence under
    `browser-uat.md`, `uat-api-evidence.json`, and screenshots, including
    `deltaBeforeCompletion=true`;
  - focused local rechecks after Checker notification passed for worker API,
    cancellation live path, and reconnect cursor path, but they do not close
    the missing standalone reconnect RED artifact;
  - Reviewer HIGH findings remain unresolved: async live worker loses
    request-provided model config, and deterministic/tool completion can still
    overwrite cancellation;
  - a partial atomic-claim repair was started before the Reviewer result was
    received, but 222.12 must not be marked complete until targeted fixes,
    RED/green evidence, Checker, and Reviewer all pass.

- 2026-07-06 `222.12` targeted reviewer-fix restart:
  - human selected option `A`;
  - Codex goal mode restarted with a contract limited to standalone reconnect
    evidence, async live worker model-config reconstruction, deterministic/tool
    cancellation non-overwrite, synthesized delta semantics, atomic worker
    claim, refreshed gates, Browser UAT, Checker round2, and Reviewer round2;
  - no new dependency, migration, real civil-aviation adapter, or live-provider
    credential work is authorized in this targeted pass.

- 2026-07-06 `222.12` targeted reviewer-fix self-gates:
  - reproduced Reviewer round1 blockers with RED artifacts for worker request
    model config, deterministic cancellation overwrite, reconnect synthetic
    delta semantics, and atomic worker claim;
  - implemented focused fixes for worker request config reconstruction,
    cancellation-safe deterministic/tool finalization, synthetic delta
    metadata, and compare-and-set worker claims;
  - refreshed focused unit, integration, contract, E2E, frontend, rem,
    frontend-full, ruff, py_compile, diff-check, and Browser UAT artifacts
    under `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/`;
  - next action is independent Checker round2 and Reviewer round2.

- 2026-07-06 `222.12` stopped at Checker/Reviewer round2:
  - saved Checker FAIL:
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round2.md`;
  - saved Reviewer FAIL:
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round2.md`;
  - Checker found focused functional gates green but round2 artifacts were
    missing at check time, so completion was not evidenced;
  - Reviewer found three unresolved blockers: mutable worker execution config,
    non-structural cancellation finalization, and inconsistent synthetic
    stream metadata on `model.stream_chunk`;
  - stop rule triggered. No further implementation is allowed without human
    direction.

- 2026-07-06 `222.12` targeted Reviewer round2 fix restart:
  - human selected option `A`;
  - authorized scope is limited to three Reviewer round2 blockers: immutable
    worker execution config semantics, structural cancellation-safe terminal
    completion, and consistent synthetic metadata on paired stream events;
  - no dependency, migration, production credential, real aviation adapter, or
    `222.11` live-provider work is authorized.

- 2026-07-06 `222.12` targeted Reviewer round3 fix restart:
  - human selected option `A`;
  - authorized scope is limited to the approval-resume cancellation event leak
    reproduced by Reviewer round3;
  - required RED must prove a run cancelled while an approved tool is executing
    does not emit a late `run.completed`;
  - no dependency, migration, production credential, real aviation adapter, or
    `222.11` live-provider work is authorized.

- 2026-07-06 `222.12` targeted Reviewer round3 fix self-gates:
  - reproduced the approval-resume cancellation event leak with
    `red-approval-resume-cancel-event.txt`;
  - fixed `approve()` so terminal completion events emit only when
    `complete_run()` returns actual `COMPLETED` status;
  - refreshed unit, integration, contract, E2E, frontend, rem, frontend-full,
    ruff, py_compile, diff-check, and Browser UAT artifacts;
  - Browser UAT used the Codex in-app browser at `/ai-assistant`, run #125,
    and saved `uat-api-evidence-round4.json` plus
    `screenshots/browser-uat-round4-viewport.png`.
  - Checker round4 passed and was recorded in
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round4.md`.
  - Reviewer round4 passed and was recorded in
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round4.md`;
    `222.12` is complete.

- 2026-07-06 `222.11` live LLM preflight restart:
  - human requested completing `222.11 Live LLM Real-Case UAT` before moving to
    `222.13`, and committing completed slices only after `222.11` completes;
  - read `loop/README.md`, `loop/CURRENT.md`, active spec `spec.md`,
    `plan.md`, `tasks.md`, and `docs/testing/acceptance-gates.md`;
  - checked process env and `.env` without printing secret values;
  - `OPENROUTER_API_KEY` and equivalent AI Assistant live-provider variables
    are missing, and no live UAT token/cost budget is configured;
  - updated `artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/preflight.md`,
    `loop/CURRENT.md`, `loop/STATE.md`, `loop/VERIFIERS.md`, and `tasks.md`;
  - stop rule fired: `222.11` remains `waiting-human` /
    `ENV-BLOCKED-LIVE-MODEL`. Deterministic or mock LLM UAT cannot satisfy this
    release gate.

- 2026-07-06 `222.11` live LLM qwen3.6 completion:
  - human confirmed OpenRouter target `qwen/qwen3.6-27b`;
  - OpenRouter `/models` confirmed slug, context length, and pricing metadata;
  - updated backend, API schema, frontend defaults, and tests from
    `qwen/qwen3.5-27b` to `qwen/qwen3.6-27b`;
  - RED captured baseline model mismatch in `red-live-llm.txt` and missing
    mock aviation default registry in `red-live-realistic-cases.txt`;
  - implemented default mock aviation adapter registration and approval-resume
    context-budget event emission;
  - live UAT passed against real OpenRouter qwen3.6 for plain raw streaming and
    refund/change/baggage/flight-disruption realistic mock aviation cases;
  - browser UAT passed on run 126 with visible plan/task/tool/context/audit and
    final-result state;
  - secret scan found no full OpenRouter key pattern in source or artifacts;
  - unit, contract, E2E, ruff, compileall, diff-check, full frontend, Checker,
    and Reviewer evidence were recorded under
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/`.

- 2026-07-06 `222.12` targeted Reviewer round2 self-gates:
  - added RED artifacts for worker config durability, terminal completion
    status guard, and synthetic `model.stream_chunk` metadata;
  - implemented queue-time/worker request model-config consistency checks
    before worker claim, repository-level protected terminal completion, and
    synthetic/non-raw/non-streaming metadata on paired stream events;
  - refreshed focused backend, frontend, rem, full frontend, ruff,
    py_compile, diff-check, and Browser UAT artifacts;
  - Browser UAT session #70 / run #124 confirmed visible completion and API
    evidence with `model.stream_chunk.streaming=false`,
    `raw=false`, and `synthetic=true`.

- 2026-07-06 `222.12` stopped at Checker/Reviewer round3:
  - saved Checker PASS:
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round3.md`;
  - saved Reviewer FAIL:
    `artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round3.md`;
  - Checker found the three Reviewer round2 blockers closed with focused
    evidence;
  - Reviewer found a remaining structural cancellation blocker in the
    approval-resume path: a cancelled `WAITING_APPROVAL` run can still receive
    a late `run.completed` event even though status remains `CANCELLED`;
  - stop rule triggered. No further implementation is allowed without human
    direction.

- 2026-07-05 startup preflight for `222.11`:
  - read the universal loop protocol, `loop/README.md`, `loop/CURRENT.md`, and
    this state file;
  - checked the spec source with `rg` and confirmed `222.11` requires external
    live LLM UAT while keeping civil aviation at the mock adapter seam;
  - checked `OPENROUTER_API_KEY`,
    `HIFY_AI_ASSISTANT_OPENROUTER_API_KEY`,
    `HIFY_AI_ASSISTANT_OPENROUTER_BASE_URL`, and
    `HIFY_AI_ASSISTANT_OPENROUTER_MODEL` in the shell and `.env` without
    printing values; no configured live provider was found;
  - found `loop/VERIFIERS.md` still describes `222.10`; do not update it while
    the live-service stop rule is active;
  - no RED tests, implementation, Checker, Reviewer, or Browser UAT were run
    for `222.11` because the required external-service contract is missing.

- Completed prior slice `222.5 SessionRuntime`.
- `222.5` final artifacts:
  - `artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/checker-round2.md`
  - `artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/reviewer-round2.md`
- Existing unrelated workflow changes are present and must remain untouched:
  `app/modules/workflow/domain/runtime_v2.py`,
  `app/modules/workflow/infra/realtime/redis_streams.py`, and
  `tests/unit/workflow/test_runtime_v2_event_source.py`.
- Discovery found existing `PromptAssembler` layer support and AI Assistant
  session `context_json`, allowing 222.6 MVP memory persistence without a new
  table or migration.
- Discovery found existing inspector usage UI, so the context-budget UI can be
  added as an inspector section rather than a broader redesign.
- 222.6 RED artifacts saved:
  `red.txt`, `red-contract.txt`, `red-e2e.txt`, and `red-frontend.txt`.
- 222.6 self-gate artifacts saved:
  `unit.txt`, `contract.txt`, `e2e.txt`, `frontend-focused.txt`,
  `frontend-rem.txt`, `frontend.txt`, `diff-check.txt`, and
  `py_compile.txt`.
- Browser UAT ran in the Codex in-app browser against
  `http://[::1]:5173/ai-assistant`, verified the inspector context section, and
  saved
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/uat.md`.
- Attempted independent Checker subagent
  `019f23d9-58a0-77d1-ad0a-a8972e35d7f7`; it errored before running checks:
  account usage limit, retry after 2026-07-03 01:24 AM per tool notification.
- Attempted independent Reviewer subagent
  `019f23d9-ad1a-7811-a56f-ea6ed0986c6c`; it errored before writing a review:
  account usage limit, retry after 2026-07-03 01:24 AM per tool notification.
- Retried independent Checker after the quota window; round1 PASS report:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/checker-round1.md`.
- Independent Reviewer round1 FAIL report:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/reviewer-round1.md`.
- Added RED evidence for Reviewer round1 findings:
  `red-reviewer-round1.txt` and
  `red-reviewer-round1-context-budget.txt`.
- Fixed:
  - real runs resolve recursive AGENTS.md from session
    `aiAssistantWorkspace.cwd`;
  - inspector reloads current session memory from `context_json` while
    preserving run instruction-memory metadata;
  - context budget separates selected `usedTokens` from raw budget pressure;
  - inspector renders raw pressure and audit references.
- Refreshed self-gate artifacts after reviewer fixes:
  `unit.txt`, `contract.txt`, `e2e.txt`, `frontend-focused.txt`,
  `frontend-rem.txt`, `frontend.txt`, `diff-check.txt`, `py_compile.txt`,
  and `uat.md`.
- Independent Checker round2 PASS report:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/checker-round2.md`.
- Independent Reviewer round2 PASS report:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/reviewer-round2.md`.
- Updated `specs/222-ai-assistant-general-harness-mvp/spec.md` and `tasks.md`
  to mark `222.6` complete and record evidence.
- Human selected option `C` for the `222.7` gate: run Open Loop design review
  first, no code or RED tests.
- Created preflight contract:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/open-loop-contract.md`.
- Initial independent Checker for `222.7-preflight` PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/checker-round1.md`.
- Initial independent Reviewer for `222.7-preflight` FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/reviewer-round1.md`.
- Fixed preflight contract and `loop/CURRENT.md`:
  - scoped `fencing_token` to AI Assistant resource locks and excluded worker
    queue leasing / SessionRuntime worker fencing changes;
  - made lock contention deterministic: no wait/retry in MVP, return
    `code=RESOURCE_LOCK_CONTENDED`, emit `resource_lock.contended`, and do not
    execute without a valid lease;
  - made shell boundary concrete: default executable allowlist remains exactly
    `node`;
  - listed required audit events and fields for permission, sandbox, and lock
    decisions;
  - made the implementation-start human gate explicit for permission,
    sandbox, DB-lock, and schema changes.
- Independent Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/checker-round2.md`.
- Independent Reviewer round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/reviewer-round2.md`.
- Human selected option `A`, resolving the `222.7` implementation human gate
  for the preflight contract boundary.
- 222.7 implementation RED artifacts saved:
  `red-unit.txt`, `red-contract.txt`, `red-e2e.txt`, and
  `red-reviewer-round1.txt`.
- 222.7 final self-gates saved:
  `unit.txt`, `integration.txt`, `contract.txt`, `e2e.txt`,
  `unit-integration-regression.txt`, `contract-e2e-regression.txt`,
  `ruff.txt`, `mypy.txt`, `mypy-harness-reviewer.txt`, `diff-check.txt`,
  `py_compile.txt`, and `uat.md`.
- Independent Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/checker-round2.md`.
- Independent Reviewer round2 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round2.md`.
- Fixed Reviewer round2 targeted mypy blocker and verified:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/mypy-harness-reviewer.txt`.
- Independent Reviewer round3 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round3.md`.
- 222.8 RED artifacts saved:
  `red-unit.txt`, `red-contract.txt`, and `red-e2e.txt`.
- 222.8 implementation added first-class `SkillRuntime` discovery/indexing,
  progressive prompt loading, on-demand skill resource reads, skill audit
  events, and high-risk `run_skill_script` planning through the ToolRuntime
  permission path. Default missing skills now degrade as `UNAVAILABLE` so
  existing ReAct chains can continue to later tools.
- 222.8 self-gates saved:
  `unit.txt`, `unit-ai-assistant.txt`, `integration.txt`, `contract.txt`,
  `contract-ai-assistant.txt`, `e2e.txt`, `e2e-ai-assistant.txt`, `ruff.txt`,
  `py_compile.txt`, `mypy-focused.txt`, `diff-check.txt`, and `uat.md`.
- Full targeted mypy including `harness.py` still reports pre-existing/import
  graph issues in `app/modules/chat/domain/llm_request.py`,
  `app/modules/ai_assistant/domain/live_model.py`, and no-any-return reports
  when imports are skipped; focused mypy on new/modified runtime modules is
  green in `mypy-focused.txt`.
- Browser UAT used the Codex in-app browser at
  `http://[::1]:5173/ai-assistant`; the first full-page screenshot was blank,
  so it was discarded and replaced with nonblank viewport evidence in
  `screenshots/uat-ai-assistant-page-viewport.png`.
- Independent Checker round1 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/checker-round1.md`.
  Checker reported live unit/contract/e2e commands failed because
  `SkillRuntime` was missing from `app.modules.ai_assistant.domain.skills`.
  Main workspace immediate rerun of the same three commands passed:
  `3 passed`, `2 passed`, and `1 passed`, indicating a Checker worktree/source
  visibility mismatch rather than a local code failure.
- Local post-Checker rerun artifacts saved:
  `local-rerun-after-checker-fail-unit.txt`,
  `local-rerun-after-checker-fail-contract.txt`, and
  `local-rerun-after-checker-fail-e2e.txt`.
- Independent Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/checker-round2.md`.
  Source-view checks confirmed `class SkillRuntime` exists and imports, then
  live unit/contract/e2e SkillRuntime gates and `git diff --check` passed.
- Independent Reviewer round1 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/reviewer-round1.md`.
- 222.9 RED artifacts saved:
  `red-unit.txt`, `red-contract.txt`, and `red-e2e.txt`.
- 222.9 implementation added `trace_audit.py`, a read-only
  `get_run_audit_export` service path, `/api/v1/ai-assistant/runs/{run_id}/audit`,
  and an eval regression for trace/audit/budget export.
- 222.9 self-gates saved:
  `unit.txt`, `contract.txt`, `e2e.txt`, `eval.txt`, `unit-focused.txt`,
  `contract-focused.txt`, `e2e-focused.txt`, `ruff.txt`, `py_compile.txt`,
  `diff-check.txt`, and `uat.md`.
- Independent Checker round1 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/checker-round1.md`.
- Independent Reviewer round1 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/reviewer-round1.md`.
  Blockers:
  - eval regression can false-pass while missing required 222.9 trace/audit
    coverage;
  - token/cost budget degradation is only tested as a pure function and not
    carried through real request -> persisted run input -> audit export;
  - focused mypy reports a modified-file type error at `trace_audit.py:350`.
- 222.9 reviewer-fix RED artifact saved:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/red-reviewer-round1.txt`.
- 222.9 reviewer-fix implementation:
  - strict eval coverage now reports `missingSpanKinds` and
    `missingAuditFields`, and partial runs no longer false-pass;
  - request schema, router, and harness persist `aiAssistantBudget` and
    `modelBudgetPolicy` into run input;
  - audit export includes token/cost caps and model degradation decisions from
    persisted run input;
  - `trace_audit.py` sort key uses typed numeric normalization.
- 222.9 reviewer-fix self-gates saved:
  `reviewer-fix-focused.txt`, refreshed `unit.txt`, `contract.txt`, `e2e.txt`,
  `unit-focused.txt`, `contract-focused.txt`, `e2e-focused.txt`, `eval.txt`,
  `ruff.txt`, `py_compile.txt`, `diff-check.txt`, `mypy-focused.txt`,
  `mypy-reviewer-scope.txt`, and `mypy-skip-imports.txt`.
- Independent Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/checker-round2.md`.
- Independent Reviewer round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/reviewer-round2.md`.
- Updated `spec.md` and `tasks.md` to mark `222.9 TraceAuditEvalBudget`
  complete and record final evidence.
  Reviewer found no blocker and confirmed scope/gates were respected for
  SkillRuntime.
- 222.10 RED artifact saved:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/red.txt`.
- 222.10 implementation added `aggregate_production_eval.py` and
  `tests/eval/test_ai_assistant_aggregate_production_eval.py`.
- 222.10 self-gates saved:
  `eval-aggregate.txt`, `unit.txt`, `contract.txt`, `e2e.txt`, `eval.txt`,
  `frontend-focused.txt`, `frontend-rem.txt`, `frontend.txt`, `ruff.txt`,
  `py_compile.txt`, `mypy-focused.txt`, `diff-check.txt`, and `uat.md`.
- Independent Checker round1 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/checker-round1.md`.
- Independent Reviewer round1 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/reviewer-round1.md`.
  Blockers:
  - aggregate eval can false-pass on synthetic evidence instead of real 222.10
    artifacts / trace exports;
  - required `aggregate-production-report.md` artifact is missing despite
    Checker PASS;
  - Docs Gate remains open because `spec.md` still marks `222.10` pending and
    `tasks.md` leaves 222.10 items unchecked.
- Human selected option `A` for targeted reviewer-fix.
- 222.10 reviewer-fix implementation:
  - added real artifact assembly to `aggregate_production_eval.py`;
  - added report writer / CLI that writes `aggregate-production-report.md` and
    `aggregate-production-report.json`;
  - added negative eval coverage for missing real audit export and open Docs
    Gate;
  - generated `aggregate-trace-audit-export.json` using the real
    `trace_audit.build_trace_audit_export()` path;
  - added a ToolRunner rate-limit unit test so timeout, 5xx, and rate-limit
    self-correction are all represented in gate evidence.
- 222.10 reviewer-fix self-gates refreshed:
  `eval-aggregate.txt` (`8 passed`), `unit.txt` (`72 passed`),
  `contract.txt` (`47 passed`), `e2e.txt` (`10 passed, 1 skipped`),
  `eval.txt` (`11 passed`), `frontend-focused.txt` (`45 passed`),
  `frontend-rem.txt` (`1 passed`), `frontend.txt` (`430 passed`),
  `aggregate-report-generation.txt`, `ruff.txt`, `py_compile.txt`,
  `mypy-focused.txt`, and `diff-check.txt`.
- Independent Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/checker-round2.md`.
- Independent Reviewer round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/reviewer-round2.md`.
  Reviewer confirmed all round1 blockers closed. Non-blocking residual risk:
  most aggregate checks still combine gate artifacts with source-text
  assertions rather than parsing every behavior directly from one runtime
  export, and the full-gate label is broader than the enforced gate set.

## Problems

- No active blocker before starting `222.8` scope discovery.
- Important boundary: `222.6` must not make `memory.md` mandatory.
- Important boundary: Session Summary and Working Memory must use existing
  AI Assistant-owned persistence, currently session `context_json`, unless a
  human gate approves a schema/migration change.
- Important boundary: AGENTS.md updates require diff plus approval-gated tool
  contract; unapproved writes are out of scope.
- Important boundary: `222.6` may add context inspector UI and frontend tests,
  but must not broaden into SkillRuntime, PermissionPolicy, SandboxRuntime,
  ResourceLock, or full TraceAuditEvalBudget.
- Important boundary for `222.7`: Open Loop preflight is not implementation
  completion. `tasks.md` remains unchecked for `222.7` implementation items.
- Important boundary for `222.7`: resource-lock `fencing_token` is scoped only
  to AI Assistant resource locks; worker queue leasing and SessionRuntime
  worker fencing remain out of scope.
- Important boundary for `222.7`: default shell executable allowlist remains
  exactly `node`; broad shell execution and network broadening are out of
  scope.
- Historical note before the later `222.11` / `222.12` reopen: Spec 222 was
  complete at that earlier point. Current status is governed by the top of this
  file and the active `spec.md` slice table.
- Important boundary for `222.8`: SkillRuntime may integrate with existing
  permission/sandbox/tool runtime, but must not add broad shell/network powers,
  new dependencies, real external side effects, or real aviation business
  behavior without a human gate.
- 222.8 caution: FastAPI `app.dependency_overrides` are process-global in the
  tests, so API contract/e2e suites that override the AI Assistant service
  should be run serially, not through parallel pytest processes.
- 222.8 blocker: Checker round1 evidence conflicts with main workspace live
  reruns. Because Checker reported FAIL, the slice cannot proceed to Reviewer
  or 222.9 without human direction.
- 222.8 blocker resolved by Checker round2 PASS and Reviewer round1 PASS.
- 222.9 human gate: TraceAuditEvalBudget includes audit export of prompts, tool
  args/results, approvals, file diffs, adapter audit, token/cost budget, and
  model fallback/degradation behavior. This touches data export and
  budget/model-policy behavior, so implementation should not begin without
  human confirmation or an Open Loop preflight decision.
- Human selected option `A`, resolving the `222.9` implementation human gate
  for the confirmed TraceAuditEvalBudget boundary.
- 222.9 RED artifacts saved:
  `red-unit.txt`, `red-contract.txt`, and `red-e2e.txt`.
- 222.9 implementation added `trace_audit.py`, a read-only
  `get_run_audit_export` service path, `/api/v1/ai-assistant/runs/{run_id}/audit`,
  and an eval regression for trace/audit/budget export.
- 222.9 self-gates saved:
  `unit.txt`, `contract.txt`, `e2e.txt`, `eval.txt`, `unit-focused.txt`,
  `contract-focused.txt`, `e2e-focused.txt`, `ruff.txt`, `py_compile.txt`,
  `diff-check.txt`, and `uat.md`.
- Independent Checker round1 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/checker-round1.md`.

## Checker Evidence

- Checker round1 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/checker-round1.md`.
- Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/checker-round2.md`.
- `222.7-preflight` Checker round1 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/checker-round1.md`.
- `222.7-preflight` Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/checker-round2.md`.
- `222.7` Checker round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/checker-round2.md`.
- Verifier list:
  `loop/VERIFIERS.md`
- `222.6` artifact directory:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/`
- `222.7-preflight` artifact directory:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/`

## Reviewer Findings

- Reviewer round1 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/reviewer-round1.md`.
- Reviewer round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/reviewer-round2.md`.
- `222.7-preflight` Reviewer round1 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/reviewer-round1.md`.
- `222.7-preflight` Reviewer round2 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7-preflight/reviewer-round2.md`.
- `222.7` Reviewer round2 FAIL:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round2.md`.
- `222.7` Reviewer round3 PASS:
  `artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round3.md`.

## Lessons

- `222.5` lesson recorded in `loop/LESSONS.md`: control tests must cover
  associated pending approvals/actions and stale decisions, not only run status.
- `222.6` lesson recorded in `loop/LESSONS.md`: when independent subagent gates
  are unavailable because of quota, stop as `waiting-human` rather than
  substituting Orchestrator self-review.
- `222.7-preflight` lesson recorded in `loop/LESSONS.md`: Open Loop contracts
  for gated safety slices must make MVP behavior 0/1 verifiable and must not
  import adjacent runtime concepts such as worker leasing/fencing by naming
  similarity alone.
