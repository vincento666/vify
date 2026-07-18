# Builder Handoff — 226.8

TDD method: `tdd`

## Scope

- Converted `/worker/process` from request-local execution to a time-bounded,
  idempotent enqueue/inspect compatibility shim.
- Split the AI Assistant registry into default production and explicit demo
  profiles. Production deployment rejects demo profile configuration.
- Passed one settings snapshot through router and standalone worker composition
  so capability selection cannot drift through global configuration.
- Removed the implicit `echo_context` request default. Deterministic no-tool
  runs now complete honestly without emitting a fake tool call.
- Added cancellation checks to the no-tool completion path after a fault test
  proved it could emit `run.completed` after `run.cancelled`.
- Renamed the misleading Customer `ControlledReActCore` to
  `CustomerTurnCoordinator` and removed unused fake iteration state.
  `RestrictedReactWorker`, its registry and policy stay as Customer business
  Adapter/configuration over the public Harness.
- Removed the inert Add Context control and migrated legacy UAT selectors from
  sequence-range processed groups to stable activities.
- Kept planning strategy because its three values have real runtime behavior.
- Recorded caller, accepted-contract and deletion decisions in `inventory.md`.

## GREEN Evidence

- AI Assistant affected unit/contract/E2E:
  `143 passed, 16 subtests passed`.
- Customer Assistant affected unit/integration/SSE plus public dependency
  contracts: `49 passed`.
- Public dependency focused gate: `7 passed`.
- Frontend full unit suite: `116 files / 482 tests passed`.
- Frontend production `vue-tsc && vite build`: PASS.
- Ruff on all touched Python paths: PASS.
- Four affected E2E scripts `node --check`: PASS.
- Scoped `git diff --check`: PASS.
- Added-line production secret scan: no match.

The Starlette `httpx` deprecation warning and Vite CJS/large-chunk warnings are
pre-existing non-blockers.

## Browser UAT

Command:

```text
HIFY_E2E_BASE_URL=http://127.0.0.1:5174 \
HIFY_E2E_ARTIFACT_DIR=artifacts/slices/226-ai-assistant-runtime-convergence-shell/226.8 \
node frontend/e2e/ai-assistant-activity-shell-uat.mjs
```

Verdict: PASS.

Verified:

- Hify light shell remains distinct from the Codex dark reference;
- running activity is expanded and completed activity is collapsed;
- manual expansion survives event upsert;
- approval and failed activities remain expanded;
- one running and one completed durable child are visible;
- live model text remains a peer timeline item;
- inert Add Context is not rendered;
- reduced-motion and zero-overflow checks pass.

Artifacts:

- `uat-runs/ai-assistant-activity-shell-uat.json`
- `screenshots/ai-assistant-light-activity-shell.png`
- `screenshots/ai-assistant-approval-error-states.png`

## Compatibility And N/A

- `/worker/process` physical deletion: blocked by unknown external-consumer
  inventory. The shim reports a 2026-08-01 target and never runs a worker in
  the request process.
- Database migration: N/A; 226.8 changes no schema.
- Live external provider: N/A; capability registry contracts and Browser UAT
  are deterministic. Live provider exit gates remain 226.9.
- Production deploy, push and merge: not authorized.

## Remaining Contract

- 226.9 runs the cross-module HA/security/runtime-v2/migration/full regression
  exit matrix and performs Product Re-entry Review.
