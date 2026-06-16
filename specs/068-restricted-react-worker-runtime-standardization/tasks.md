# Tasks 068: Restricted ReAct Worker Runtime Standardization

## 068.0 Sign-off

- [x] Confirm this standardizes one worker, not the assistant main runtime.
- [x] Confirm tool registry is allowlisted.
- [x] Confirm high-risk tools become proposed actions.
- [x] Confirm default tests use fake/deterministic tools and models.
- [x] Confirm raw chain-of-thought/internal reasoning is never emitted.

## 068.1 Worker Contract

- [x] RED: restricted ReAct worker output fails structured schema validation.
- [x] Define structured action/observation/final schemas.
- [x] Add schema version fields and redaction rules.
- [x] Validate final output.

## 068.2 Tool Registry And Policy

- [x] RED: unsupported tool call is not blocked.
- [x] Add tool registry.
- [x] Add policy gate.
- [x] Classify tools as read-only, proposed-write, or blocked.
- [x] Add idempotency key handling for retryable side-effecting tool calls.
- [x] Add proposed action path for high-risk calls.

## 068.3 Eventful Loop

- [x] Emit standardized L2 ReAct events.
- [x] Emit structured summaries only, not raw hidden reasoning.
- [x] Enforce max iterations, token/cost budget, and wall-clock timeout.
- [x] Integrate timeout/cancel semantics from worker runtime.

## 068.4 Compatibility

- [x] Prove existing worker result fields remain compatible.
- [x] Run customer-assistant worker tests.

## Evidence

- RED:
  `artifacts/slices/068-restricted-react-worker-runtime-standardization/red.txt`
- Focused green:
  `artifacts/slices/068-restricted-react-worker-runtime-standardization/focused.txt`
- Backend gates:
  `artifacts/slices/068-restricted-react-worker-runtime-standardization/backend-gates.txt`
  (`15 passed, 1 warning`)
- Browser UAT:
  `artifacts/slices/068-restricted-react-worker-runtime-standardization/uat.md`
  and `artifacts/slices/068-restricted-react-worker-runtime-standardization/screenshots/browser-uat-restricted-react-worker.png`
