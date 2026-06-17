# Plan: 148.1 Worker Cancel Unsupported UI

## Slice

Connect the existing backend worker cancel endpoint to the customer-assistant
operator workbench.

1. Add RED frontend API/runtime/panel assertions.
2. Add `cancelCustomerAssistantWorkerRun(workerRunId)` to the API module.
3. Add `cancelCustomerAssistantRuntimeWorkerRun(current, workerRunId)` that calls
   cancel and then reuses `refreshCustomerAssistantRuntimeLedgers`.
4. Render a worker-level `请求取消` button for running task rows with async
   worker refs.
5. Extend the worker refresh browser UAT to click the worker cancel button and
   assert unsupported-cancel events render.

## Verification

- Focused frontend API/runtime/panel tests.
- `remScaleClosure`.
- Full frontend unit and build.
- Browser UAT with screenshot.
