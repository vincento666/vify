# 184.4 Phase 3 Conversation List And Right Inspector

## Modification Scope

- Added read-only run listing and run inspector API endpoints.
- Added inspector projection for active task, tool calls, approval queue,
  recent errors, timeline, elapsed time, and token placeholders.
- Upgraded the AI Assistant product shell to left session/run list, center
  event echo, and right run/task inspector.
- Restored the shell colors to Hify's light content-area style.
- Added Playwright browser E2E coverage for echo, approval, inspector, and
  light-shell rendering.

## RED Evidence

- `red-backend.txt`: inspector API contract failed before endpoint/projection
  implementation.
- `red-frontend.txt`: frontend API and shell contract failed before session
  list and inspector UI.

## Gates

- `backend-contract.txt`: inspector API contract passed.
- `backend-focused.txt`: AI Assistant backend unit/integration/contract/E2E
  focused suite passed.
- `frontend-focused.txt`: AI Assistant frontend focused tests passed.
- `frontend-unit.txt`: full frontend unit suite passed.
- `remScaleClosure.txt`: frontend rem gate passed.
- `e2e.txt`: Playwright product-shell E2E passed.

## Remaining Risks

- The task list is derived from run/event state for Phase 3. A durable task
  ledger and scheduler remain deferred to follow-up specs.
- Token counts are placeholders until observability/accounting lands in a
  later spec.
