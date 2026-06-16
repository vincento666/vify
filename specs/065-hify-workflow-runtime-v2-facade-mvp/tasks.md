# Tasks 065: Hify Workflow Runtime V2 Facade MVP

## 065.0 Sign-off

- [x] Confirm this is Hify Workflow, not an external workflow system.
- [x] Confirm shared runtime core is mandatory.
- [x] Confirm legacy Workflow endpoint compatibility remains mandatory.
- [x] Confirm Workflow debug UI consumes v2 async refs/events in v2 mode.
- [x] Confirm Workflow v2 uses a published/snapshot definition.
- [x] Confirm Workflow facade does not use Chatflow session semantics.
- [x] Confirm external router caller context is preserved without moving SOP
      routing ownership into Workflow v2.

## 065.1 Workflow V2 Route

- [x] RED: Workflow v2 run contract test fails because no v2 facade exists.
- [x] Add Workflow v2 run route or explicit v2 mode.
- [x] Return status/result/event refs.
- [x] Record workflow version/snapshot metadata.
- [x] Preserve caller context metadata in refs/events where supplied.
- [x] Support idempotent create when request key is supplied.

## 065.2 Supported Graph Execution

- [x] Run a supported deterministic Workflow graph through shared runtime v2.
- [x] Emit pre-terminal run/node events.
- [x] Fetch final result through result ref.

## 065.3 Unsupported Graph Handling

- [x] RED: unsupported Workflow graph partially executes.
- [x] Add unsupported graph report or full-run fallback.

## 065.4 Legacy Compatibility

- [x] Prove existing Workflow sync run response remains compatible.
- [x] Prove existing debug/observe surfaces still work.
- [x] Distinguish v2 live events from legacy/debug replay in diagnostics.
- [x] Prove Workflow debug run uses v2 async status/events instead of replay
      when v2 mode is selected.

## 065.5 Canvas Debug Projection

- [x] RED: Workflow canvas node animation/status cannot update from v2 events.
- [x] Project node `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, and `SKIPPED`
      states to canvas/debug consumers.
- [x] Stop debug run and mark failed when a node emits failure without supported
      error/fallback path.
- [x] Update debug panel with real-time node status while run is active.

## 065.6 Gates

- [x] Run workflow focused tests.
- [x] Run Browser UAT on Workflow debug surface.
- [x] Verify canvas node running animation, completed state, waiting state, and
      failed state follow runtime v2 events.
- [x] Verify debug panel receives real-time node status updates.
- [x] Verify node error stops the run and shows failure.

Evidence:

- RED: `artifacts/slices/065-hify-workflow-runtime-v2-facade-mvp/red.txt`
- Integration: `artifacts/slices/065-hify-workflow-runtime-v2-facade-mvp/integration.txt`
- Backend gates: `artifacts/slices/065-hify-workflow-runtime-v2-facade-mvp/backend-gates.txt`
- Browser UAT: `artifacts/slices/065-hify-workflow-runtime-v2-facade-mvp/uat.md`
