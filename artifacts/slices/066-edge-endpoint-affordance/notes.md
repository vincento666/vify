# 066 Edge And Endpoint Affordance Audit

## Scope

- Verified chatflow/workflow edge insert button visibility for the reported ghost-button risk.
- Verified endpoint hover/selected scaling and connection-preview scaling radius for the reported magnetic-snap mismatch.
- No product code change was required in this slice; current implementation already satisfies the focused behavior gates.

## Evidence

- `chatflow-edge-insert-button-visibility.mjs`
  - hover shows one insert button;
  - leaving both edge and button hides it;
  - selected edge keeps it visible;
  - pane click clears selection and hides it.
- `chatflow-endpoint-affordances.mjs`
  - node hover/selection scales endpoints to 1.2x;
  - endpoint hover scales to 1.5x.
- `chatflow-endpoint-connection-radius.mjs`
  - dragging a connection within 42px of the target endpoint, inside the 44px magnetic radius, scales the target endpoint to 1.5x.
- Browser UAT on `http://127.0.0.1:5173/workflows/5529/canvas`
  - selected edge showed one insert button;
  - clicking the VueFlow pane cleared it to zero visible insert buttons.

## Gates

- E2E edge insert visibility: passed.
- E2E endpoint affordance: passed.
- E2E endpoint connection radius: passed.
- Frontend focused unit: `flowGraph.test.ts` and `canvasControls.test.ts` passed.
- Frontend REM: `remScaleClosure.test.ts` passed.
- Frontend full unit: 58 files / 188 tests passed.
- Frontend build: passed.
