# 047 Edge Insert Visibility UAT

Date: 2026-06-08

Target: `http://127.0.0.1:5173/workflows/4685/canvas`

Checks:

- Selected an existing canvas edge and verified exactly one edge insert button became visible.
- Clicked a non-edge toolbar control (`调试工具`).
- Verified the selected edge state was cleared.
- Verified visible edge insert button count returned to `0`.
- Verified the debug dock could open without leaving an orphaned edge insert button on the canvas.

Automated coverage:

- `chatflow-edge-insert-button-visibility.mjs` covers hover show, hover leave hide, selected edge persistence, and external click clear.
- `chatflow-edge-interactions.mjs` covers selected-edge width and edge insertion palette behavior.
- `chatflow-edge-insert-branch.mjs` covers branch edge insertion and auto split/reconnect.

Evidence:

- Screenshot: `artifacts/slices/047-edge-insert-visibility/screenshots/browser-uat-edge-insert-hidden.png`
- Browser-observed final counts: visible insert buttons `0`, selected edge paths `0`.
