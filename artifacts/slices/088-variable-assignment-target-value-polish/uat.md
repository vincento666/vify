## Browser UAT

- Date: 2026-06-08
- Page: `http://127.0.0.1:5173/workflows/{id}/canvas`
- Scope:
  - Variable assignment target cannot be typed as an arbitrary new variable.
  - Assignment value uses the shared input-or-reference split control.
  - Redundant source type column/select is removed.
  - Newly added variable assignment nodes no longer prefill `flow.value`.
  - Existing workflow/chatflow assignment runtime still writes scoped variables.
- Result: PASS via Playwright browser UAT.
- Screenshot: `screenshots/assignment-panel.png`

## Gates

- RED source-type/readonly: `red.txt`
- RED default target: `red-default-target.txt`
- E2E assignment: `e2e-assignment.txt`
- Unit flow graph: `unit-flow-graph.txt`
- Rem/unit gate: `rem-unit.txt`
- Full frontend unit: `full-unit.txt`
- Integration: `integration.txt`
- Frontend build: `build.txt`
