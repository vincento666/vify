# Plan: Workflow Runtime V2 Cancel Debug Control

## Slice 104.1 Canvas Debug Cancel Control

1. Add RED frontend tests for `cancelRuntimeV2Run` and `workflow_run_cancelled` projection.
2. Implement the smallest frontend API and debug projection changes.
3. Add a debug dock cancel button guarded by active runtime v2 state.
4. Wire the button to cancel, refresh runtime v2 detail, and update status/output.
5. Verify with focused unit tests, rem gate, build, and browser UAT.

## Test Strategy

- Unit: `frontend/src/api/workflowRuntimeV2.test.ts`
- Unit: `frontend/src/views/workflow/runtimeV2Debug.test.ts`
- Rem: `frontend/src/remScaleClosure.test.ts`
- Browser UAT: `frontend/e2e/workflow-runtime-v2-cancel-debug-control.mjs`

## Risk Notes

- The debug dock is a large Vue file; keep UI edits limited to the existing dock header and runtime v2 state helpers.
- Existing backend cancel is already covered by spec 102; do not duplicate backend behavior here.
- Use existing rem-sized button styles and lucide icons so the control fits the debug dock header on narrow layouts.
