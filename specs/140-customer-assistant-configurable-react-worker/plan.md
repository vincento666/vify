# Plan

## Status

Complete.

## Slice 140.1 Profile-Driven ReAct Registry

1. Add RED integration coverage proving a persisted worker profile can route a
   task to `react_worker` but cannot yet constrain the ReAct tool allowlist.
2. Derive ReAct worker configs from the effective worker-profile catalog.
3. Use a dispatching ReAct worker so each task resolves config by
   `taskType + workerRef`.
4. Preserve the existing default `refund_status_react` config when no profile
   override exists.
5. Run focused MySQL8 integration and customer-assistant regression gates.
