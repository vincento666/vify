# Tasks 063: Hify Chatflow Runtime V2 Facade MVP

## 063.0 Sign-off

- [x] Confirm Chatflow v2 facade must use the shared core from 062.
- [x] Confirm first supported paths stay minimal.
- [x] Confirm old Chatflow endpoint compatibility remains mandatory.
- [x] Confirm node-level v1/v2 mixed execution is forbidden.
- [x] Confirm facade events are projections of the shared runtime event store.
- [x] Confirm resume is idempotent for the same checkpoint/input.
- [x] Confirm Chatflow debug UI consumes v2 async refs/events in v2 mode.
- [x] Confirm external router caller context is preserved without moving SOP
      routing ownership into Chatflow v2.

## 063.1 Shared Core Facade

- [x] RED: Chatflow v2 facade test fails because refs/events are not produced
      through shared runtime core.
- [x] Connect Chatflow v2 facade to shared runtime core.
- [x] Preserve event refs and result refs.
- [x] Preserve caller context metadata in refs/events where supplied.
- [x] Avoid duplicate authoritative Chatflow-only event storage.

## 063.2 Minimal Paths

- [x] Prove `START -> MESSAGE -> END`.
- [x] Prove `START -> QUESTION -> resume -> END`.
- [x] Persist session/checkpoint projections.
- [x] Add duplicate-resume guard for the same checkpoint/input.

## 063.3 Unsupported Graph Handling

- [x] RED: unsupported graph attempts partial mixed execution.
- [x] Add unsupported graph report or full-run fallback.
- [x] Include unsupported node keys and node types.
- [x] Prove fallback/rejection does not emit fake v2 live refs.

## 063.4 Compatibility

- [x] Prove legacy sync response shape remains compatible.
- [x] Prove legacy SSE replay remains separate from v2 live events.
- [x] Prove Chatflow debug run uses v2 async status/events instead of replay
      when v2 mode is selected.

## 063.5 Canvas Debug Projection

- [x] RED: Chatflow canvas node animation/status cannot update from v2 events.
- [x] Project node `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, and `SKIPPED`
      states to canvas/debug consumers.
- [x] Stop debug run and mark failed when a node emits failure without supported
      error/fallback path.
- [x] Update debug panel with real-time node status while run is active.

## 063.6 Browser UAT

- [x] Verify v2 live event progress in Chatflow debug surface.
- [x] Verify canvas node running animation, completed state, waiting state, and
      failed state follow runtime v2 events.
- [x] Verify debug panel receives real-time node status updates.
- [x] Verify node error stops the run and shows failure.
- [x] Verify reconnect by `runId` and `afterSequence`.
- [x] Save screenshots and notes.

Evidence:

- RED unsupported facade: `artifacts/slices/063-hify-chatflow-runtime-v2-facade-mvp/red.txt`
- RED resume idempotency: `artifacts/slices/063-hify-chatflow-runtime-v2-facade-mvp/red-resume-idempotency.txt`
- Backend gates: `artifacts/slices/063-hify-chatflow-runtime-v2-facade-mvp/backend-gates.txt`
- Browser UAT: `artifacts/slices/063-hify-chatflow-runtime-v2-facade-mvp/uat.md`
