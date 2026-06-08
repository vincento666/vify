## Browser UAT

- Date: 2026-06-08
- Page: `http://127.0.0.1:5173/workflows/{id}/canvas`
- Scope:
  - Variable aggregation panel hides the old advanced compatibility section.
  - Tool, knowledge, subworkflow, and agent resource node panels hide advanced compatibility debug/raw id fields.
  - Legacy config values remain accepted by the structured editors and runtime.
- Result: PASS via Playwright browser UAT.
- Screenshots:
  - `screenshots/resource-panels.png`
  - `screenshots/variable-aggregation.png`

## Gates

- RED: `red.txt`
- Unit: `unit-node-config.txt`
- E2E resource panels: `e2e-resource-panels.txt`
- E2E variable aggregation: `e2e-variable-aggregation.txt`
- Rem/unit gate: `rem-unit.txt`
- Full frontend unit: `full-unit.txt`
- Frontend build: `build.txt`
