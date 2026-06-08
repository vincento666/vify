# 100 Endpoint Scale Baseline UAT

- Date: 2026-06-09
- Page: `http://127.0.0.1:5173/workflows/6217/canvas`
- Browser: in-app Browser

## Checks

- Verified endpoint CSS hitbox width/height is `2.25rem`, equal to `0.75rem * 3`.
- Verified connected source endpoint center is aligned with the node right edge within canvas transform tolerance.
- Verified endpoint vertical center matches the node card vertical center.
- Saved screenshot: `artifacts/slices/100-endpoint-scale-baseline/in-app-endpoint-uat.png`.

## Notes

- The in-app Browser CUA mouse move did not reliably trigger CSS `:hover` on the VueFlow endpoint, so hover scale behavior is covered by Playwright E2E.
- Playwright E2E confirms node hover uses `2x`, direct endpoint hover uses `3x`, and leaving the endpoint hitbox falls back to node hover scale.
