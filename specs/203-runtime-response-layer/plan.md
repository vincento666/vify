# Plan

## 203.1 Runtime Result Response Summary

1. RED contract: assert the runtime result endpoint returns the Phase 8 summary
   fields and compact events while the full events endpoint remains detailed.
2. GREEN implementation: enrich `ChatflowRuntimeV2Service.get_result` with
   summary fields derived from the run, node runs, and runtime events.
3. Gates: focused contract, runtime/workflow backend regression, frontend rem
   closure, full frontend unit, and browser UAT reuse of the workflow gateway.

## Risk Controls

- Do not remove existing `output`, `checkpoint`, or full event APIs.
- Do not expose `payload.output` inside the simplified `events` list.
- Keep the slice limited to response formatting.
