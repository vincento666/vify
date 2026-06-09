# UAT

Date: 2026-06-09

Targets:
- http://127.0.0.1:5173/chatflows/create
- http://127.0.0.1:5173/workflows/create

Validation:
- Collapsing the chatflow left settings panel leaves the full canvas visible, with START/END nodes and the default connection rendered.
- Collapsing the workflow overview panel leaves the full canvas visible, with START/END nodes rendered.
- Re-expanding either panel does not blank or reset the canvas.
- Existing chatflow settings and readonly variable-panel regressions still pass.

Local screenshot:
- `artifacts/slices/121-left-panel-collapse-canvas-visibility/uat-left-panel-collapse.png`
