# 070 Node Panel Product Audit

- Focus: selector/condition node operand controls.
- RED: `red-condition-operand-control.txt` proves the old condition row did not render split operand controls.
- E2E: `e2e-condition-operand-control-two-row.txt` and `e2e-condition-branch-endpoints.txt` passed.
- Frontend gates: `unit-focused-rem.txt`, `unit-full.txt`, and `build.txt` passed.
- Browser UAT: `browser-uat-condition-control.json` captured the in-app browser state with two operand controls, persistent left/right picker buttons, a left clear button, and a readable left variable chip.
- Screenshots:
  - `screenshots/browser-condition-panel-before.png`
  - `screenshots/condition-operand-control-two-row.png`
  - `screenshots/browser-uat-condition-control.png`

Remaining audit scope after this slice:
- Full node panel matrix for variable assignment, variable aggregation, JSON parse, intent recognition, API, agent, LLM, message, information collection, knowledge retrieval, and plugin/resource nodes.
- Condition node still needs deeper branch runtime/product audit for multi-condition editing beyond the split operand control fixed here.
