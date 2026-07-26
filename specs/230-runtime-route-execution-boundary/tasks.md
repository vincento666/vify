# Tasks — Spec 230

Status: accepted; blocked until Spec 229 Goal Gate.

TDD method: `tdd`.

## 230.0 Contract Gate

- [x] ADR 0010 accepted.
- [x] conversation/session surface, permissions, outcomes, receipt lifetime,
  effect classification, opt-in owner enforcement, and non-goals frozen.
- [ ] Spec 229 Goal Gate linked before activation.

Evidence: `artifacts/slices/230-runtime-route-execution-boundary/230.0/`

## 230.1 Trusted Principal And Proposal

- [ ] RED identity/tenant/read/operate/permission/local-bypass matrix.
- [ ] GREEN trusted context binding and pure proposal/gate models.
- [ ] Session create/message/stream/task/event/trace Contract and audit
  serialization.
- [ ] Security Checker/Reviewer; commit/push.

Evidence: `artifacts/slices/230-runtime-route-execution-boundary/230.1/`

## 230.2 Pre-mutation Route Gate

- [ ] RED missing-read permission and zero task/child calls for
  FAQ/RAG/clarify/no-match/safe Agent answer.
- [ ] RED zero-call assertions for every mutating action.
- [ ] GREEN read-answer gate plus one fail-closed dispatch gate before
  mutation/adapter.
- [ ] Existing SOP/fallback regression.
- [ ] Security Checker/Reviewer; commit/push.

Evidence: `artifacts/slices/230-runtime-route-execution-boundary/230.2/`

## 230.3 Confirmation, Stale State, Idempotency, Audit

- [ ] RED expiry/reuse/cross-tenant/stale/parallel cases.
- [ ] GREEN bounded single-purpose receipt and durable audit.
- [ ] Add Alembic + contract/integration tests only if persistence changes.
- [ ] Browser confirmation and stale-retry UAT.
- [ ] Security Checker/Reviewer; commit/push.

Evidence: `artifacts/slices/230-runtime-route-execution-boundary/230.3/`

## 230.4 Child Side-effect Authorization

- [ ] RED missing/tampered receipt executes a RuntimeLab-owned side effect.
- [ ] RED unknown/write tool or delegated child exceeds authority; ordinary
  Message/Variable Assign is over-gated.
- [ ] GREEN server-owned effect classification, owner-aware enforcement, and
  authorization propagation.
- [ ] Prove no success event/effect record on deny.
- [ ] Full non-RuntimeLab runtime regression.
- [ ] Fresh security review; commit/push.

Evidence: `artifacts/slices/230-runtime-route-execution-boundary/230.4/`

## 230.5 Contract C Goal Gate

- [ ] Threat matrix, Unit/Contract/Integration/E2E/Browser/Docs all green.
- [ ] Independent Checker `ALL GREEN`.
- [ ] Fresh-context Reviewer `PASS`.
- [ ] Update Loop snapshot; commit/push; advance only to Spec 231.

Evidence: `artifacts/slices/230-runtime-route-execution-boundary/230.5/`

## Stop Rules

- trusted identity or permission semantics cannot be inferred;
- non-RuntimeLab owners need breaking migration;
- real production write/IAM/deploy becomes required;
- any Critical/High security finding remains after bounded repair;
- fresh-context Reviewer capability unavailable.
