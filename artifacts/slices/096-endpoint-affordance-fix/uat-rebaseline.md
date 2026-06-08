## 096 endpoint affordance rebaseline UAT

- Browser target: `http://127.0.0.1:5173/workflows/6217/canvas`
- Screenshot: `artifacts/slices/096-endpoint-affordance-fix/screenshots/in-app-endpoint-uat-visible.png`
- Default geometry measured in the in-app browser:
  - node: `variable_aggregation_1`
  - source endpoint center X: `431.3233`
  - node right edge: `431.8995`
  - target endpoint center X: `261.7226`
  - node left edge: `261.1464`
  - left/right edge alignment delta: `< 1px`
- Hover animation gate: covered by `frontend/e2e/chatflow-endpoint-affordances.mjs`
  - node hover dot scale: `2x`
  - endpoint hover dot scale: `3x`
  - hit box width remains unchanged between default and hover
  - endpoint hover still responds within the magnetic radius
- Browser CUA note: direct `tab.cua.move` in the in-app browser did not trigger CSS `:hover` in this session; product hover behavior was therefore verified through Playwright E2E and the in-app browser was used for geometry and visual screenshot.
