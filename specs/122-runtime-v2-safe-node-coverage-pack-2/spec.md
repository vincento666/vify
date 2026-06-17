# Feature Spec: Runtime V2 Safe Node Coverage Pack 2

## Status

Complete. Backend-only SDD+TDD slice 122.1.

## Problem

Runtime v2 powers the productized Workflow/Chatflow demo, but some safe MVP node
types still fall through missing/unknown node behavior. Product demos need
predictable evidence for safe core nodes without enabling unsafe external side
effects.

## Scope

- Add or confirm async runtime-v2 coverage for `EXECUTE_WORKFLOW`.
- Add or confirm async runtime-v2 coverage for `TRANSFER_TO_HUMAN`.
- Preserve existing unknown-node safety semantics.
- Preserve run metadata, event ordering, checkpoint updates, and lifecycle
  behavior consistent with existing runtime-v2 nodes.

## Out of Scope

- Real child workflow execution across persisted workflow definitions.
- Real human-operator queue integration.
- Frontend/customer-assistant changes.
- New external network or tool side effects.

## Functional Requirements

1. `EXECUTE_WORKFLOW` emits visible node start and completion events in runtime
   v2.
2. `EXECUTE_WORKFLOW` returns deterministic mock child-workflow output suitable
   for demos and automated regression evidence.
3. `TRANSFER_TO_HUMAN` emits visible transfer/handoff evidence and enters a safe
   waiting or resumable runtime state using existing runtime-v2 lifecycle
   vocabulary.
4. Resuming after `TRANSFER_TO_HUMAN` continues the run without losing metadata
   or checkpoint history.
5. Cancelling a run blocked at `TRANSFER_TO_HUMAN` follows existing cancel
   lifecycle behavior.
6. Unknown or missing node behavior remains safe and covered by existing
   regressions.

## Acceptance Criteria

- RED tests demonstrate missing coverage before implementation: `red.txt`.
- Focused workflow runtime-v2 tests pass after implementation: `focused.txt`.
- Existing runtime-v2 regression tests remain green:
  `runtime-v2-regression.txt`.
- `ruff` passes for touched backend files/tests: `ruff.txt`.
- Browser UAT is documented as not applicable for this backend-only runtime
  slice: `uat.md`.
- Evidence is saved under
  `artifacts/slices/122-runtime-v2-safe-node-coverage-pack-2/122.1/`.

## Delivered Behavior

- `EXECUTE_WORKFLOW` is admitted by runtime-v2 compatibility checks and executes
  as a deterministic side-effect-free mock child workflow. It preserves input
  mappings, output mappings, node start/completion events, node-run output, and
  run metadata.
- `TRANSFER_TO_HUMAN` is admitted for runtime-v2 graphs and blocks with a
  checkpoint, `workflow_node_waiting`, and `handoff_requested` event evidence.
  Resuming supplies the handoff result and continues the graph; cancelling from
  the interrupted state reuses the existing runtime-v2 cancel lifecycle.
- Unknown nodes such as `LLM` remain rejected by compatibility checks.
