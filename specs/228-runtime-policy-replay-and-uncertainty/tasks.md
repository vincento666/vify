# Tasks — Spec 228

Status: active; next unit `228.4`.

TDD method for all implementation units: `tdd`.

## 228.0 Contract Gate

- [x] Problem, baseline, outcome, scope, non-goals, public compatibility, and
  authority frozen.
- [x] Success predicate, max attempts, TTL, provider budget, exhaustion action,
  review context, evidence paths, branch, and worktree recorded.
- [x] Downstream boundaries assigned to Specs 229-231.
- [x] User authorized commit and push; merge/deploy/live-provider remain denied.
- [x] Contract Checker `ALL GREEN` and Reviewer `PASS` evidence recorded before
  implementation.

Evidence: `artifacts/slices/228-runtime-policy-replay-and-uncertainty/228.0/`

## 228.1 Real-route Evaluation Contract

- [x] Run `tdd` preflight and record method.
- [x] RED: missing injected real-route runner and false-green negative case.
- [x] GREEN: `RouteEvalCase`, required/known-gap status, deterministic report,
  metrics, and zero-provider default.
- [x] Unit and missing-evidence negative gates.
- [x] Checker/Reviewer; commit `test(runtime-policy): add real route eval contract`.

Evidence: `artifacts/slices/228-runtime-policy-replay-and-uncertainty/228.1/`

## 228.2 Governance Replay Integrity

- [x] RED: candidate profile changes real route output but static replay does
  not detect it.
- [x] GREEN: injected replay port; remove parallel decision truth.
- [x] MySQL parity through public RuntimeLab command path.
- [x] Contract/E2E replay APIs and historical comparison.
- [x] Checker `ALL GREEN`; Reviewer `PASS`; commit
  `fix(runtime-policy): replay shared route decisions` pushed as `5affc1eb`.

Evidence: `artifacts/slices/228-runtime-policy-replay-and-uncertainty/228.2/`

## 228.3 Server-owned Uncertainty

- [x] RED: real LLM low/invalid confidence or explicit clarification mutates a
  task.
- [x] GREEN: shared uncertainty policy; bootstrap `0.60`; release validation.
- [x] Prove zero task/adapter mutation on every uncertainty branch.
- [x] Preserve legacy profile readability without silent mutation.
- [x] Final Checker `ALL GREEN`; Reviewer `PASS`; commit
  `fix(runtime-lab): enforce route uncertainty`.

Evidence: `artifacts/slices/228-runtime-policy-replay-and-uncertainty/228.3/`

## 228.4 Targeted Clarification

- [x] RED: targeted question is replaced by generic menu.
- [x] GREEN: additive route/API/log/replay/frontend projection.
- [x] Contract, E2E, idempotent replay, Browser UAT, screenshot/report.
- [x] Checker `ALL GREEN`; Reviewer `PASS`; commit
  `feat(runtime-lab): preserve targeted clarification` pushed as `ef02934b`.

Evidence: `artifacts/slices/228-runtime-policy-replay-and-uncertainty/228.4/`

## 228.5 Contract A Goal Gate

- [ ] Required eval cases pass; known gaps remain visible.
- [ ] Full Spec 228 verifier, diff, secret, migration, API/SSE regression.
- [ ] Independent Checker `ALL GREEN`.
- [ ] Independent Reviewer `PASS`.
- [ ] Update Loop snapshot; commit and push.
- [ ] Advance only to accepted Spec 229.

Evidence: `artifacts/slices/228-runtime-policy-replay-and-uncertainty/228.5/`

## Stop Rules

- MySQL or browser unavailable: record `ENV-BLOCKED-*`; recover capability or
  wait, never PASS.
- Shared engine extraction expands beyond routing decision behavior: stop.
- Existing API action semantics require a breaking change: stop.
- Three failed directed repair rounds: `WAITING_HUMAN`.
- Any live/paid provider requirement, merge, or deploy: stop for authority.
