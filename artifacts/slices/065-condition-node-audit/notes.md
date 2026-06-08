# 065 Condition Node Audit

## Scope

- Reverted the unrequested left-panel variable insertion detour before this slice.
- Audited the workflow condition/selector node only:
  - card shows semantic branch rows instead of generic input/output rows;
  - branch names are editable from the config header and reflected on the card;
  - source endpoints align with each branch row;
  - config panel uses branch blocks, priorities, and condition rows instead of an all/any form section;
  - variable value input uses the existing reference picker behavior covered by focused E2E.

## Result

No product code change was required in this slice. The previously mentioned endpoint snap/animation work is not part of the remaining condition-node gap; focused gates show the condition node card/config/runtime path is already covered.

## Gates

- Frontend E2E: `workflow-condition-branch-endpoints.mjs` passed.
- Frontend E2E: `workflow-condition-branch-values.mjs` passed.
- Backend integration: `tests/integration/workflow/test_workflow_condition_run.py` passed via `uv run pytest`.
- Frontend REM: `src/remScaleClosure.test.ts` passed.
- Frontend focused unit: `src/views/workflow/nodeConfig.test.ts` passed.
- Frontend full unit: 58 files / 188 tests passed.
- Frontend build: passed.
