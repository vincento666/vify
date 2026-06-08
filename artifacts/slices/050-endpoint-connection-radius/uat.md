# 050 Endpoint Connection Radius UAT

Date: 2026-06-08

Target behavior:

- The canvas keeps `connection-radius` at `44`.
- While dragging a connection, a target endpoint must visually scale to `1.5x` at `42px` from its center, i.e. inside the same magnetic radius instead of only on direct hover.
- Existing node hover and endpoint hover affordances must remain unchanged.
- Real edge insertion and selected-edge behavior must remain unchanged.

Checks:

- RED: `chatflow-endpoint-connection-radius.mjs` failed at `42px` with ratio `1`.
- GREEN: the same test passed after adding Hify's connection preview endpoint state.
- Regression: `chatflow-endpoint-affordances.mjs` passed.
- Regression: `chatflow-edge-interactions.mjs` passed.
- Regression: `chatflow-edge-insert-branch.mjs` passed.
- Unit/rem: focused rem/canvas controls tests passed.
- Full frontend unit and build passed.

Browser UAT:

- The in-app browser was opened on the workflow canvas.
- Direct dynamic inspection through in-app CUA was not used as final evidence because its drag helper releases the mouse before DOM sampling.
- The saved Playwright browser screenshot captures the real `mouse.down()` drag state before `mouse.up()`, which is the authoritative visual evidence for this mid-drag animation.

Evidence:

- Screenshot: `artifacts/slices/050-endpoint-connection-radius/screenshots/e2e-endpoint-radius.png`
