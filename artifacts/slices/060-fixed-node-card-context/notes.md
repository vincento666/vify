# 060 Fixed Node Card Context

Scope:
- Fixed chatflow/workflow fixed-node card labels so START card exposes output variables and END card exposes input variables.
- Kept END config panel return/output editor semantics unchanged; the canvas card now reflects data-flow semantics.
- Hardened keyboard deletion regression for START/END nodes and verified adding a normal node does not recreate fixed nodes.

Red:
- `red-chatflow-fixed-node-deletion.txt` captured the old mismatch: START still rendered `输入` and END still rendered `输出`.

Gates:
- `rtk node frontend/e2e/chatflow-fixed-node-card-labels.mjs` -> `e2e-chatflow-fixed-node-card-labels.txt`
- `HIFY_E2E_SCREENSHOT=artifacts/slices/060-fixed-node-card-context/screenshots/chatflow-fixed-node-deletion.png rtk node frontend/e2e/chatflow-fixed-node-deletion.mjs` -> `e2e-chatflow-fixed-node-deletion.txt`
- `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` -> `rem.txt`
- `rtk npm --prefix frontend run test:unit` -> `unit-full.txt`
- `rtk npm --prefix frontend run build` -> `build.txt`
