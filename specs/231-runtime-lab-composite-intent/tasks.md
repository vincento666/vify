# Tasks — Spec 231

Status: accepted; blocked until Spec 230 Goal Gate.

TDD method: `tdd`.

## 231.0 Contract Gate

- [x] atomic component, relation, resolution, ledger, expiry, compatibility,
  and non-goals frozen.
- [x] current composite regression and zero-mutation predicate recorded.
- [ ] Spec 230 Goal Gate linked before activation.

Evidence: `artifacts/slices/231-runtime-lab-composite-intent/231.0/`

## 231.1 Atomic Component Detection

- [ ] Run `tdd` preflight.
- [ ] RED: refund-plus-invoice silently starts one SOP.
- [ ] RED: duplicate/invented component and wrong-relation cases.
- [ ] GREEN: pure component model, bounded cues, strict candidate membership.
- [ ] Unit/single-intent regression, Checker/Reviewer.
- [ ] Commit and push `feat(runtime-lab): detect composite intent components`.

Evidence: `artifacts/slices/231-runtime-lab-composite-intent/231.1/`

## 231.2 Sequencing Clarification And Pending Plan

- [ ] RED: composite detection mutates task or loses component/order evidence.
- [ ] GREEN: targeted question and detected/resolved/expired ledger events.
- [ ] Expiry, replay, stale, cross-session, and changed-candidate negatives.
- [ ] Integration zero-call assertions and additive Contract tests.
- [ ] Checker/Reviewer; commit and push.

Evidence: `artifacts/slices/231-runtime-lab-composite-intent/231.2/`

## 231.3 Consultation Plus Transaction

- [ ] RED: transaction starts in the answer turn or unsafe answer is treated as
  deterministic.
- [ ] GREEN: read-only answer plus explicit offer; fresh-gated acceptance.
- [ ] Active/suspended, permission, confirmation, and child-effect regression.
- [ ] E2E and Browser UAT with route inspector evidence.
- [ ] Checker/Reviewer; commit and push.

Evidence: `artifacts/slices/231-runtime-lab-composite-intent/231.3/`

## 231.4 Contract D And Program Goal Gate

- [ ] All required composite cases pass with provider usage `0`.
- [ ] Full Specs 228-231 verifier, API/SSE, migration, frontend, diff, and
  secret gates pass.
- [ ] Independent Checker `ALL GREEN`.
- [ ] Independent Reviewer `PASS`; no unresolved security Critical/High.
- [ ] Update Loop snapshot, create final slice commit, and push.
- [ ] Stop at delivery gate; merge/PR/deploy remain unauthorized.

Evidence: `artifacts/slices/231-runtime-lab-composite-intent/231.4/`

## Stop Rules

- parser expansion is no longer bounded by frozen RED cases;
- representation requires a generic DAG/table or concurrent active tasks;
- resolution cannot re-enter the Spec 230 gate;
- a Browser/MySQL gate is unavailable after bounded capability recovery;
- three failed directed repair rounds or unresolved security Critical/High;
- merge, PR, deployment, production write, or live provider becomes required.
