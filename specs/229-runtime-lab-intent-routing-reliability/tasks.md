# Tasks — Spec 229

Status: accepted; blocked until Spec 228 Goal Gate.

TDD method: `tdd`.

## 229.0 Contract Gate

- [x] Candidate, context, catalog, retrieval, metrics, non-goals, and public
  compatibility frozen.
- [x] Code-first Catalog and zero-live-provider policy accepted.
- [ ] Spec 228 Goal Gate evidence linked before activation.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.0/`

## 229.1 Canonical Candidate Fusion

- [ ] RED duplicate, tie, conflict, and Top-K cases.
- [ ] GREEN deterministic fusion and additive provenance.
- [ ] Existing candidate/semantic policy regression.
- [ ] Checker/Reviewer; slice commit and push.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.1/`

## 229.2 Post-fusion Margin

- [ ] RED low-margin classifier selection mutates state.
- [ ] GREEN `candidateMinMargin=0.12` across policy/config/replay/logs.
- [ ] Contract and mutation-free Integration/E2E.
- [ ] Checker/Reviewer; slice commit and push.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.2/`

## 229.3 Read-only RouteContextSnapshot

- [ ] RED multi-turn ellipsis and child-state parity.
- [ ] GREEN snapshot builder and bounded/redacted classifier projection.
- [ ] Prove zero state mirrors/writes and payload <= 12 KiB.
- [ ] Browser multi-turn UAT.
- [ ] Checker/Reviewer; slice commit and push.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.3/`

## 229.4 Versioned Intent Catalog

- [ ] RED duplicate/invalid/confusable/version instability cases.
- [ ] GREEN code-first definitions, validation, deterministic version.
- [ ] Route/eval/API evidence.
- [ ] Checker/Reviewer; slice commit and push.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.4/`

## 229.5 Isolated Intent Retriever

- [ ] RED recall and answer-corpus isolation cases.
- [ ] GREEN deterministic retriever port/implementation.
- [ ] Architecture dependency and no-answer-snippet gates.
- [ ] Recall@5 and Macro-F1 targets.
- [ ] Checker/Reviewer; slice commit and push.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.5/`

## 229.6 Contract B Goal Gate

- [ ] All quality targets and full RuntimeLab regression pass.
- [ ] Browser report/screenshots and Docs evidence complete.
- [ ] Independent Checker `ALL GREEN`; Reviewer `PASS`.
- [ ] Update Loop snapshot; commit/push; advance only to Spec 230.

Evidence: `artifacts/slices/229-runtime-lab-intent-routing-reliability/229.6/`

## Stop Rules

- any new execution-state mirror;
- provider-backed embedding or new dependency needed;
- public breaking change;
- quality target missed after three directed attempts;
- MySQL/browser capability unavailable without approved recovery.
