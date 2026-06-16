# 078 Plan

## 078.1 Backend Demo Access Boundary

- Add a small customer-assistant access policy modeled after the evaluation
  target policy: local source is allowed, embedded host calls require the
  relevant permission.
- Inject `RequestContext` into the customer-assistant service factory.
- Classify routes as read or operate at the FastAPI boundary.
- Persist sanitized request-context metadata into newly created assistant
  session context.
- Keep response envelopes and `/api/v1/customer-assistant/...` paths unchanged.
- Add a browser UAT script that sends browser-side fetches through the frontend
  dev proxy and verifies denied/allowed host contexts.

TDD seams:

- RED contract test: embedded host without `customer_assistant:operate` receives
  403 when creating a session or submitting a turn.
- RED contract test: embedded host with permissions can run the existing session
  loop.
- RED integration test: session context stores tenant/operator metadata and
  redacts tokens/phone/order values from supplied context.

## 078.2 Response Redaction And Ref Ownership

- Apply central sanitizer to public task/event/action/worker/sub-agent response
  payloads.
- Persist or derive owner context for sessions and deny cross-tenant access to
  secondary references.
- Cover `runId`, `actionId`, `workerRunId`, session ledger, and SSE payload
  access with RED tests before implementation.

## 078.3 Workbench Host Context UAT

- Run browser UAT with `window.__HIFY_HOST__` containing tenant, actor, source,
  and `customer_assistant:*` permissions.
- Prove the workbench can create/load a demo story, confirm an action, and fetch
  metrics under host context.
- Save screenshot and evidence.

## Gates

Each slice saves RED, focused tests, full relevant regression, docs evidence,
and commits independently. Frontend visual code changes also require rem and
full frontend unit gates.
