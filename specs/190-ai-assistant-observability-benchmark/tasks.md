# Tasks 190: AI Assistant Token And Cost Usage

## Historical Completed Work

- [x] 190.0 documentation sign-off.
- [x] 190.1 backend observability tracer and deterministic benchmark snapshot.
- [x] 190.2 historical 184-190 aggregate acceptance evidence.

Benchmark expansion is cancelled. Historical benchmark fields may remain for
compatibility but create no open work.

## Superseded Backlog — Not Planned

- multi-scenario benchmark suites;
- governance policy checks;
- budget enforcement, alerts, SLO, billing, or cross-user admin;
- generic frontend observability dashboard.

## Contract Revision

- [x] Freeze one immutable ledger row per model call.
- [x] Freeze session and current user/workspace total granularity.
- [x] Freeze date/session/provider/model/token-type dimensions.
- [x] Freeze provider actual cost, versioned estimate, then unknown precedence.
- [x] Freeze dashboard cards, heatmap, details, distributions, composition,
  Token/Cost toggle, and range filter.
- [x] Freeze benchmark/governance/alerts/budget as out of scope.

## 190.3 Per-Call Usage Ledger

- [ ] TDD preflight and observable RED.
- [ ] Add Alembic migration and MySQL8 model-usage ledger.
- [ ] Persist trusted user/workspace/session/run/call scope.
- [ ] Normalize provider/model and token dimensions per call.
- [ ] Keep unavailable optional dimensions null.
- [ ] Finalize one streaming-call row from provider terminal usage.
- [ ] Keep cache/reasoning as breakouts without total double-count.
- [ ] Capture normal planner model calls.
- [ ] Capture Spec 188 memory-extractor calls when available.
- [ ] Prevent duplicate/replayed call double-counting.
- [ ] Save migration/integration/contract evidence and pass Checker/Reviewer.

## 190.4 Versioned Cost And Aggregate API

- [ ] TDD preflight and observable RED.
- [ ] Implement fixed-decimal provider actual cost.
- [ ] Implement versioned price-table estimate.
- [ ] Represent unknown price as null with explicit counters.
- [ ] Preserve historical pricing version and cost.
- [ ] Add scoped summary, daily, sessions, dimensions, and detail endpoints.
- [ ] Add timezone-correct buckets and range validation.
- [ ] Reconcile per-call, session, period, and cumulative totals.
- [ ] Save API/E2E evidence and pass Checker/Reviewer.

## 190.5 Token/Cost Dashboard

- [ ] TDD preflight and observable frontend RED.
- [ ] Add /ai-assistant/usage route and AI Assistant entry.
- [ ] Add today, yesterday, 30-day, and cumulative cards.
- [ ] Add recent-year daily Token/Cost heatmap.
- [ ] Add default 30-day range filter and Token/Cost toggle.
- [ ] Add session ranking/detail.
- [ ] Add provider/model distribution and token-type composition.
- [ ] Add loading, empty, partial-cost, unknown-price, and error states.
- [ ] Run frontend tests, rem gate, and repeatable Browser UAT.
- [ ] Save screenshots/DOM evidence and pass Checker/Reviewer.

## 190.6 Aggregate Acceptance

- [ ] Reconcile ledger, APIs, inspector, and dashboard.
- [ ] Rerun backend, frontend, migration, isolation, and UAT gates.
- [ ] Prove planner and memory-extractor usage capture.
- [ ] Prove no benchmark/governance/alerts/budget/cross-user scope.
- [ ] Save final Checker/Reviewer reports and residual risks.
