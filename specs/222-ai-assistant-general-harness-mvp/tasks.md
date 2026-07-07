# Tasks 222: AI Assistant General Harness MVP

## 222.0 Boundary Rebase

- [x] Create `specs/222-ai-assistant-general-harness-mvp/spec.md`.
- [x] Create `specs/222-ai-assistant-general-harness-mvp/plan.md`.
- [x] Create `specs/222-ai-assistant-general-harness-mvp/tasks.md`.
- [x] Update `loop/CURRENT.md` to point at the active spec and clarify
      Plan/Task planning strategies.
- [x] Create loop operational files for this docs sprint without treating them
      as alternate spec sources.
- [x] Update `specs/README.md` directory index and natural execution order.
- [x] Run docs-sprint verifier commands from `loop/VERIFIERS.md`.
- [x] Save documentation evidence under
      `artifacts/slices/222-ai-assistant-general-harness-mvp/222.0/`.

## 222.1 PlanTaskRuntime And UI

- [x] RED: backend tests fail for missing first-class plan/task state.
- [x] RED: contract tests fail for missing planning strategy and plan/task
      inspector payload.
- [x] RED: frontend tests fail for missing current task, recognized needs,
      planned steps, active step, current tool, approval point, and final
      result.
- [x] Implement `planning_strategy` values:
      `auto_lightweight`, `deliberate`, `plan_only`.
- [x] Implement plan/task persistence or safe JSON-backed storage.
- [x] Emit `plan.created`, `plan.step_started`, `plan.step_completed`,
      `plan.revised`, `plan.blocked`, `task.created`, `task.updated`,
      `task.completed`, and `task.blocked`.
- [x] Render plan/task UI while keeping debug JSON in the inspector.
- [x] Run backend, frontend, rem, E2E, Browser UAT, and docs gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/build.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.1/uat.md
```

## 222.2 StreamingRuntime

- [x] RED: backend contract tests fail until provider deltas are emitted before
      completion.
- [x] RED: frontend tests fail until token deltas render incrementally.
- [x] Implement raw text delta events.
- [x] Implement heartbeat, Last-Event-ID, afterSequence replay, run snapshot,
      and frontend reconnect.
- [x] Mark non-streaming providers as explicit fallback.
- [x] Run streaming unit, contract, E2E, Browser UAT, and docs gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/build.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.2/uat.md
```

## 222.3 ToolRuntime And Adapter Seam

- [x] RED: unit tests fail for ToolRunner timeout, retry/backoff/jitter,
      circuit breaker, fallback, idempotency key, and structured error.
- [x] RED: model-observation tests fail until tool failures return structured
      observations for replan.
- [x] RED: adapter seam tests fail for missing `BusinessToolAdapter` schema,
      risk, idempotency, compensation, and audit fields.
- [x] Implement unified ToolRunner.
- [x] Route all tools through ToolRunner.
- [x] Implement `BusinessToolAdapter` interface.
- [x] Implement mock aviation adapter without real aviation rules.
- [x] Add aviation-style eval fixtures for refund, change ticket, baggage, and
      flight disruption.
- [x] Run backend unit, integration, contract, E2E, eval, and docs gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/red-reviewer-round2.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/red-reviewer-round3.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/red-reviewer-round4.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/red-reviewer-round5.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/red-reviewer-round6.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/eval.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.3/uat.md
```

## 222.4 FileWorkspace

- [x] RED: tests fail for missing read/list/search/edit/write/apply_patch.
- [x] RED: edit tests fail for exact match, context match, whitespace
      tolerance, unique candidate checks, diff preview, checksum/mtime
      preconditions, atomic write, rollback snapshot, and file lock.
- [x] Implement file workspace tools.
- [x] Ensure concurrent writes cannot overwrite each other.
- [x] Ensure failed edits do not damage files.
- [x] Run file workspace unit, integration, contract, E2E, Browser UAT, and
      docs gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/red-reviewer-round1.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.4/uat.md
```

## 222.5 SessionRuntime

- [x] RED: lifecycle tests fail for missing durable queue/worker, checkpoint,
      pause, resume, cancel, snapshot, heartbeat, and reconnect recovery.
- [x] Replace FastAPI BackgroundTasks for AI Assistant runs with durable queue
      and worker semantics.
- [x] Persist run checkpoints and stream cursors.
- [x] Implement pause/resume/cancel.
- [x] Restore pending approvals, plan progress, emitted tokens, and tool state
      after refresh/reconnect.
- [x] Run lifecycle unit, integration, contract, E2E, Browser UAT, and docs
      gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/red-reviewer-round1.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.5/reviewer-round2.md
```

## 222.6 MemoryContext And ContextBudget

- [x] RED: prompt tests fail until nearest recursive AGENTS.md instructions are
      layered into prompt context.
- [x] RED: persistence tests fail until DB-backed session summary and working
      memory reload.
- [x] RED: context-budget tests fail until usage percentage, compaction delta,
      prompt layer token share, selected/dropped layers, and drop reasons are
      recorded.
- [x] Implement Instruction Memory through AGENTS.md read path.
- [x] Add approval-gated AGENTS.md update tool contract.
- [x] Implement DB-backed session summary.
- [x] Implement working memory key-value facts with source, timestamp, status,
      and delete/invalidate support.
- [x] Implement `context_budget` and `compaction_snapshot`.
- [x] Emit `context.budget_estimated`, `context.compaction_started`,
      `context.compaction_completed`, `context.layer_selected`, and
      `context.layer_dropped`.
- [x] Add inspector context section with usage percentage, compaction ratio,
      layer share, warning level, and audit links.
- [x] Run memory/context unit, integration, contract, E2E, Browser UAT, and
      docs gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/red-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/red-e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/red-frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/red-reviewer-round1.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/red-reviewer-round1-context-budget.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/frontend-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/frontend-rem.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/reviewer-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.6/reviewer-round2.md
```

## 222.7 PermissionPolicy, SandboxRuntime, And ResourceLock

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

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/red-unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/red-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/red-e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/red-reviewer-round1.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-fix-unit-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round2-focused-tests.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/unit-integration-regression.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/contract-e2e-regression.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/live-qwen-regression.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/stream-observability-session-regression.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/ruff.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/mypy.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/mypy-harness-reviewer.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.7/reviewer-round3.md
```

## 222.8 SkillRuntime

- [x] RED: skill tests fail for missing directory discovery and metadata index.
- [x] RED: prompt tests fail until SKILL.md is loaded only after trigger match.
- [x] RED: audit tests fail for missing skill load and resource-read events.
- [x] Implement progressive skill discovery and loading.
- [x] Read references/scripts/assets on demand only.
- [x] Add version/checksum metadata.
- [x] Integrate skill risk/policy and optional script/tool invocation through
      ToolRuntime.
- [x] Run skill unit, integration, contract, E2E, Browser UAT, docs,
      independent Checker, and independent Reviewer gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/red-unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/red-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/red-e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/unit-ai-assistant.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/contract-ai-assistant.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/e2e-ai-assistant.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/ruff.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/mypy-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/reviewer-round1.md
```

Final gate status:

```text
Builder self-gates are green locally. Checker round1 reported FAIL because its
live test commands saw an old source view where `SkillRuntime` was missing.
Checker round2 resolved the mismatch by proving `SkillRuntime` exists/imports
in its source view and then passing the live SkillRuntime unit, contract, e2e,
and diff-check gates. Reviewer round1 passed with no blockers.

Local post-Checker rerun evidence:

artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/local-rerun-after-checker-fail-unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/local-rerun-after-checker-fail-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.8/local-rerun-after-checker-fail-e2e.txt
```

## 222.9 TraceAuditEvalBudget

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

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/red-unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/red-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/red-e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/red-reviewer-round1.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/eval.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/reviewer-fix-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/unit-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/contract-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/e2e-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/ruff.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/mypy-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/mypy-reviewer-scope.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/reviewer-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.9/reviewer-round2.md
```

Final gate status:

```text
Checker round1 passed the initial trace/audit export implementation. Reviewer
round1 failed because the eval gate could false-pass, runtime budget/model
degradation was not persisted through real runs, and focused mypy found a
modified-file issue in `trace_audit.py`.

Human selected option `A` for a targeted reviewer-fix. The fix added negative
eval tests, persisted `aiAssistantBudget` and `modelBudgetPolicy` from request
to run input, exported token/cost caps and degradation decisions, and fixed the
typed sort key. Checker round2 and Reviewer round2 passed.
```

## 222.10 Aggregate Production Evaluation

- [x] Prove token-level realtime output by default.
- [x] Prove explicit fallback for non-streaming providers.
- [x] Prove refresh/reconnect recovery.
- [x] Prove tool timeout/5xx/rate-limit self-correction.
- [x] Prove safe concurrent file writes.
- [x] Prove approval, sandbox, budget, and resource-lock enforcement.
- [x] Prove context window usage percentage and compaction ratio are visible.
- [x] Prove prompt layer token share is visible and audited.
- [x] Prove on-demand skill loading.
- [x] Prove mock aviation adapter seam only.
- [x] Export complete audit evidence for at least one aggregate run.
- [x] Run full backend, frontend, rem, E2E, Browser UAT, eval, and docs gates.

Evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/red-reviewer-round1.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/eval-aggregate.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/eval.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/frontend-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/frontend-rem.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/ruff.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/mypy-focused.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/aggregate-trace-audit-export.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/aggregate-production-report.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/aggregate-production-report.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/reviewer-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.10/reviewer-round2.md
```

Gate status:

```text
Reviewer round1 failed because the initial aggregate report path could
false-pass on synthetic evidence, the required markdown report artifact was
missing, and docs remained pending. Human selected option `A` for a targeted
reviewer-fix.

The reviewer-fix adds real artifact assembly from 222.10 gate outputs,
workspace source assertions, docs state, UAT evidence, and a generated
trace/audit export. The aggregate report is now generated from those real
artifacts instead of caller-supplied synthetic booleans.

Checker round2 and Reviewer round2 passed. Reviewer noted a non-blocking
residual risk that most aggregate checks still combine gate artifacts with
source-text assertions rather than parsing every behavior directly from a
runtime export, but the round1 false-pass blocker is closed.
```

## 222.11 Live LLM Real-Case UAT

Status: `complete`.

Boundary decision:

```text
On 2026-07-05, MVP acceptance was corrected: civil-aviation remains at the
original mock adapter seam boundary, while realistic user cases must be
exercised through an external live LLM. Deterministic local model UAT is no
longer sufficient for final MVP completion.
```

Human-gate prerequisites before implementation:

- [x] Provide external live LLM provider/model/base URL/secret name and token
      budget: OpenRouter `qwen/qwen3.6-27b`,
      `https://openrouter.ai/api/v1`, runtime `OPENROUTER_API_KEY` injection,
      conservative live UAT limits.
- [x] Confirm cost and quota budget for repeated live automated UAT: use only a
      small scripted scenario set with capped `maxTokens`, stop on
      quota/rate/provider errors.
- [x] Confirm realistic UAT prompts/cases, including refund, change ticket,
      baggage, and flight disruption through the mock aviation adapter seam.
- [x] Confirm approval policy, idempotency expectations, compensation metadata,
      and audit redaction rules for simulated high-risk adapter actions.

Implementation tasks after the human gate:

- [x] RED: live LLM test fails until a real provider emits `text.delta` before
      completion and records provider metadata, token/cost, and context budget.
- [x] RED: live LLM resume test fails until snapshot plus SSE continuation
      works against a real provider run.
- [x] RED: live realistic-case UAT fails until refund, change ticket, baggage,
      and flight disruption scenarios execute with the real LLM path and mock
      aviation adapter seam.
- [x] Prove the existing mock aviation adapter still exposes tool schema, risk
      level, idempotency key, compensation transaction, and audit fields for
      the aviation-style scenarios.
- [x] Route all mock adapter calls through ToolRunner, PermissionPolicy,
      SandboxRuntime, ResourceLock, context/cost budget, trace spans, and audit
      export during live LLM UAT.
- [x] Implement live LLM automated UAT scripts using the real application API
      and real browser automation.
- [x] Add browser UAT that verifies plan/task/tool/context/audit/final-result
      visibility for at least one seeded live-LLM realistic run.
- [x] Ensure missing live LLM credentials, quota, network, or model access produce
      `waiting-human` / blocked artifacts, not PASS and not silent skip.
- [x] Run full backend, frontend, rem, E2E, live LLM, realistic-case Browser
      UAT, eval, Checker, Reviewer, and docs gates.

Required evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/preflight.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/red-live-llm.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/red-live-realistic-cases.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/live-llm-uat.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/live-realistic-cases-uat.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/screenshots/
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/audit-export-redacted.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.11/reviewer-round1.md
```

## 222.12 Real-Time Streaming And Durable Worker Correction

Status: `complete`.

Purpose:

```text
Close the P0 gap where streaming can become post-completion replay and queued
run execution can be triggered by opening the SSE endpoint.
```

Human-gate prerequisites before implementation:

- [x] Confirm whether this slice may change database schema or must use the
      existing AI Assistant tables.
- [x] Confirm worker claim/lease/heartbeat semantics and stale-worker recovery
      expectations.
- [x] Confirm pause/cancel interruption behavior for in-flight model/tool calls.
- [x] Confirm Browser UAT should use the current in-app browser at
      `/ai-assistant`.

Implementation tasks after confirmation:

- [x] RED: contract test fails while `/runs/{id}/events/stream` processes a
      queued run synchronously before returning SSE frames.
- [x] RED: E2E test fails until queued runs can execute through a worker path
      without opening the stream endpoint.
- [x] RED: streaming test fails until at least one `text.delta` is observable
      while the run status is non-terminal.
- [x] RED: reconnect/resume test fails until snapshot plus SSE continuation
      works for a worker-started run.
- [x] RED: pause/cancel test fails until running work observes control state at
      a cooperative checkpoint or records a safe deferred interruption.
- [x] RED: async live worker test fails until worker request model config is
      used without persisting raw API keys.
- [x] RED: deterministic tool cancellation test fails until terminal
      cancellation cannot be overwritten by final completion.
- [x] RED: reconnect replay test fails until synthesized deltas are marked
      non-raw, non-streaming, and synthetic.
- [x] RED: repository test fails until worker claims are compare-and-set.
- [x] Remove synchronous queued-run execution from the SSE route.
- [x] Implement durable worker claim/lease/checkpoint behavior within the
      approved data-model boundary.
- [x] Ensure stream route is subscribe/replay only and emits heartbeat/cursor
      events without starting execution.
- [x] Preserve worker request model config for live async runs without storing
      raw API keys in the queued checkpoint.
- [x] Prevent deterministic/tool finalizers from overwriting cancelled runs.
- [x] Distinguish provider raw token deltas from synthesized replay/fallback
      deltas.
- [x] Run focused backend, E2E, frontend event-stream, Browser UAT, and docs
      self-gates.
- [x] Run Checker round2. Latest result: FAIL.
- [x] Run Reviewer round2. Latest result: FAIL.
- [x] RED: worker config durability test fails until a queued run cannot
      execute under a divergent worker request model.
- [x] RED: terminal completion race test fails until completion is guarded by
      current run status.
- [x] RED: stream chunk metadata test fails until synthetic final-answer
      chunks mirror `text.delta` raw/streaming/synthetic semantics.
- [x] Fix Reviewer round2 findings.
- [x] Refresh focused backend, frontend, rem, ruff, compile, diff-check, and
      Browser UAT artifacts.
- [x] Run Checker round3. Latest result: PASS.
- [x] Run Reviewer round3. Latest result: FAIL.
- [x] Human selected option `A`: authorize a targeted Reviewer round3 fix for
      approval-resume cancellation event leakage only.
- [x] RED: approval-resume cancellation test fails until a run cancelled after
      approved tool execution starts cannot emit a late `run.completed`.
- [x] Guard approval-resume terminal finalization events against current
      cancelled run state.
- [x] Refresh focused backend, frontend, rem, ruff, compile, diff-check, and
      Browser UAT artifacts after the targeted fix.
- [x] Run Checker round4. Latest result: PASS.
- [x] Run Reviewer round4. Latest result: PASS.

Required evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-stream-route.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-worker-e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-reconnect.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-control.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-live-worker-config.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-deterministic-cancel.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-atomic-claim.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-worker-config-durability.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-complete-run-status-guard.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-synthetic-stream-chunk.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/red-approval-resume-cancel-event.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/live-worker-config-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/deterministic-cancel-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reconnect-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/atomic-claim-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/worker-config-durability-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/complete-run-status-guard-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/synthetic-stream-chunk-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/approval-resume-cancel-event-green.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/frontend-rem.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/frontend-full.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/ruff.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/uat-api-evidence.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/uat-api-evidence-round4.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/screenshots/
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round2.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round3.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round3.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/checker-round4.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.12/reviewer-round4.md
```

## 222.13 Tool Observation Self-Correction Correction

Status: `complete`.

Purpose:

```text
Close the P0 gap where structured tool-error observations can finalize a run
immediately instead of feeding a repair/replan loop.
```

Implementation tasks after confirmation:

- [x] RED: unit tests fail for recoverable timeout, 5xx, and rate-limit
      observations that currently terminate the run too early.
- [x] RED: contract tests fail until structured tool observations are visible
      to the model/orchestrator as repair input.
- [x] RED: E2E test fails until one bad tool call is repaired by retry,
      argument change, fallback adapter, or plan revision and then completes.
- [x] RED: budget test fails until the self-correction loop stops at configured
      retry, token, cost, or tool-budget limits.
- [x] Feed recoverable tool observations back into the orchestrator/executor
      loop.
- [x] Emit `plan.revised` or `task.updated` for repair attempts.
- [x] Preserve structured terminal failure for permission, sandbox, approval,
      and exhausted-budget cases.
- [x] Record trace spans, audit events, retry/fallback metadata, and budget
      usage for every repair attempt.
- [x] Run focused backend, contract, E2E, Browser UAT, Checker, Reviewer, and
      docs gates.

Required evidence:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/red-unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/red-contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/red-e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/red-budget.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/frontend.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/frontend-rem.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/ruff.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/py_compile.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/diff-check.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/browser-uat-dom.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/screenshots/browser-uat-self-correction.png
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/audit-export.json
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/reviewer-round1.md
```

## 222.14 Production Hardening Backlog

Status: `proposed-confirmation`.

Purpose:

```text
Track P1 production-hardening work that should not be treated as already
complete by the MVP slice labels.
```

Candidate tasks:

- [ ] DB-backed ToolRunner idempotency ledger and circuit breaker state.
- [ ] Event sequence concurrency safety with unique conflict retry or run-level
      sequence lock.
- [ ] Context compaction that materializes reliable summaries of dropped
      context, with source message/event ids and summary hash.
- [ ] Explicit sandbox boundary docs and tests distinguishing policy-level
      sandbox controls from OS/container isolation.
- [ ] Optional OS/container/network/CPU/memory isolation only after a separate
      dependency and architecture human gate.

Required evidence after this slice is activated:

```text
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/preflight.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/red.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/unit.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/integration.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/contract.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/e2e.txt
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/browser-uat.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/checker-round1.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14/reviewer-round1.md
```
