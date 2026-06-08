## Browser UAT

- Date: 2026-06-08
- Page: `http://127.0.0.1:5173/chatflows/create`
- Scope:
  - Hovering an edge shows the middle insert button.
  - Moving away hides the insert button.
  - Selecting an edge keeps the edge selected without leaving the insert button visible.
  - Endpoint hover/snap radius regressions remain green.
- Result: PASS
- Screenshot: `screenshots/edge-insert-hover-only.png`

## Gates

- RED: `red.txt`
- E2E edge hover-only: `e2e-edge.txt`
- E2E node picker regression: `e2e-palette.txt`
- E2E endpoint radius regression: `e2e-endpoint-radius.txt`
- E2E endpoint affordance regression: `e2e-endpoint-affordances.txt`
- Rem/unit gate: `rem-unit.txt`
- Full frontend unit: `full-unit.txt`
- Frontend build: `build.txt`
