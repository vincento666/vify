Browser UAT: PASS

- URL: `http://127.0.0.1:5173/workflows/6217/canvas`
- Scenario: open the variable aggregation node config panel from the existing workflow canvas.
- Expected: the canvas surface and node card keep their original visual scale when the right config panel opens.
- Result: before/after `.coze-flow` width stayed `877`; before/after variable aggregation node width stayed `170.75308227539062`; viewport transform stayed `none`.
- Screenshot: `artifacts/slices/098-config-panel-node-scale-stability/screenshots/uat-variable-aggregation-panel.png`
