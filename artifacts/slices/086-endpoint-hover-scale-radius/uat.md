## Browser UAT

- Date: 2026-06-08
- Scope:
  - Node hover scales visible source/target endpoints to `2x`.
  - Direct endpoint hover scales the endpoint to `3x`.
  - The expanded hover hit area triggers `3x` scale at `42px` from the endpoint center.
  - Connection drag preview scales the magnetic target endpoint to `3x` inside the `44px` snap radius.
- Result: PASS via Playwright browser UAT.
- Screenshots:
  - `screenshots/endpoint-affordances-node-hover.png`
  - `screenshots/endpoint-affordances-endpoint-hover.png`
  - `screenshots/endpoint-affordances-endpoint-radius-hover.png`
  - `screenshots/endpoint-connection-radius.png`

## In-App Browser Note

The current in-app browser reload was blocked by Browser Use URL policy during this slice, so the UAT evidence uses the project Playwright browser scenarios instead of trying to bypass the policy.

## Gates

- RED: `red.txt`
- Unit + endpoint E2E: `unit-e2e.txt`
- Rem gate: `rem-unit.txt`
- Full frontend unit: `full-unit.txt`
- Frontend build: `build.txt`
