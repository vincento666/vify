# Tasks 062: Hify Workflow/Chatflow Shared Runtime V2 Core

## 062.0 Sign-off

- [x] Confirm this is Hify Workflow/Chatflow runtime, not an external workflow
      framework.
- [x] Confirm shared core must support both `WORKFLOW` and `CHATFLOW` facades.
- [x] Confirm node-level mixed v1/v2 execution is out of scope.
- [x] Confirm old endpoints remain compatible.
- [x] Confirm persisted runtime events are the source of truth.
- [x] Confirm canvas/debug state is projected from runtime v2 events/status.
- [x] Confirm runtime create/resume requests are idempotent.
- [x] Confirm background execution does not reuse request-scoped DB sessions.

## 062.1 Runtime Event Store

- [x] RED: runtime event contract test fails because shared event store is
      missing.
- [x] Add or specify shared runtime event persistence.
- [x] Implement or document MySQL 8-safe sequence strategy.
- [x] Preserve event replay by `afterSequence`.
- [x] Add event envelope schema version and redaction rules.

## 062.2 Runtime Refs

- [x] RED: shared runtime cannot produce status/result/event refs for both owner
      types.
- [x] Add runtime ref builder for `WORKFLOW` and `CHATFLOW`.
- [x] Add idempotent create/resume request key handling.
- [x] Add status/result/event list contract.
- [x] Add node status/list contract for canvas/debug consumers.

## 062.3 Event Sink

- [x] RED: graph execution cannot emit through a runtime event sink.
- [x] Add event sink interface.
- [x] Add L1 run/node event helpers.
- [x] Add `node_status_changed` or equivalent event projection for UI updates.
- [x] Preserve caller context fields needed by external SOP routing layers.

## 062.4 Graph Compatibility

- [x] RED: unsupported graph cannot be detected before runtime.
- [x] Add graph-level compatibility checker.
- [x] Report unsupported nodes and unsupported edge/resume patterns.
- [x] Prove unsupported graph does not partially execute as mixed v1/v2.
- [x] Report unsupported graph fallback reason without taking over external SOP
      routing decisions.

## 062.5 Runner Semantics

- [x] RED: background runtime runner fails after request session closes.
- [x] Ensure runner opens its own session/unit of work.
- [x] Add monotonic terminal status transition tests.
- [x] Add node failure test proving downstream scheduling stops by default.
- [x] Add cancellation-unsupported or cancellation-supported event contract.

## 062.6 Gates

- [x] Run workflow/chatflow focused backend tests.
- [x] Save architecture notes under
      `artifacts/slices/062-hify-workflow-chatflow-shared-runtime-v2-core/`.

Evidence:

- RED: `artifacts/slices/062-hify-workflow-chatflow-shared-runtime-v2-core/red.txt`
- Compatibility RED: `artifacts/slices/062-hify-workflow-chatflow-shared-runtime-v2-core/red-compatibility.txt`
- Node failure RED: `artifacts/slices/062-hify-workflow-chatflow-shared-runtime-v2-core/red-node-failure.txt`
- Backend gates: `artifacts/slices/062-hify-workflow-chatflow-shared-runtime-v2-core/backend-gates.txt`
- Architecture notes: `artifacts/slices/062-hify-workflow-chatflow-shared-runtime-v2-core/architecture-notes.md`
