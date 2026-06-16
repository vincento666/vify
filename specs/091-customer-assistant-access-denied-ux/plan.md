# Plan 091

## 091.1 Stream Preflight And Persistent Denials

- Add RED contract coverage for cross-tenant session and worker event streams
  failing before `StreamingResponse` starts.
- Add RED frontend contract coverage that action/control permission failures are
  written into the persistent workbench error state.
- Preflight customer-assistant session/worker ownership before constructing SSE
  responses.
- Share a small panel helper for action/control catch blocks so all denied
  mutations update the failed-state alert consistently.

## Gates

- RED contract/frontend failures before implementation.
- Green focused customer-assistant contract tests.
- Green focused frontend unit tests for runtime/panel interaction contracts.
- Frontend rem gate because a Vue file is touched.
- Full frontend unit suite and production build.
- Browser UAT through the existing customer-assistant access-boundary script,
  including cross-tenant session and worker stream denials.
