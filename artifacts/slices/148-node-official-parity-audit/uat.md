# 148 Node Official Parity Audit

## Official Reference

- Coze Code node docs: `research/coze-code-node.json`; screenshot: `screenshots/coze-code-node.png`.
  - Code node declares input variables, runs code, returns an object, defines output parameters, supports Python and JavaScript.
  - IDE offers code generation/templates and parameter completion.
- Coze Condition node docs: `research/coze-condition-node.json`; screenshot: `screenshots/coze-condition-node.png`.
  - Condition node is if/else branching, supports multiple branch conditions, AND/OR conditions, and drag-priority branches.
- Coze Variable merge docs: `research/coze-variable-merge-node.json`; screenshot: `screenshots/coze-variable-merge-node.png`.
  - Variable merge returns the first non-empty value in each same-type group.
- Coze Variable assign docs: `research/coze-variable-assign-node.json`; screenshot: `screenshots/coze-variable-assign-node.png`.
  - Variable assign writes user/application variables; system variables are read-only.

## Slice Scope

- Fixed Code node parity first:
  - Frontend schema now exposes Python and JavaScript.
  - Code field uses a dedicated code-editor UI with a basic template insertion action.
  - Runtime supports JavaScript `async function main({ params }) { return {...} }`.
- Variable aggregation and assignment are documented for follow-up slices; existing grouped first-non-empty path remains covered.

## Gates

- RED: `red.txt`
- Unit + integration: `unit-integration.txt`
- E2E: `e2e-transform.txt`
- Frontend rem: `rem.txt`
- Full frontend unit: `full-unit.txt`
- Build: `build.txt`

## Browser UAT

- `workflow-transform-nodes.mjs` opened workflow and chatflow canvases, exercised Code/Text/JSON nodes, opened the Code node panel, verified the dedicated code editor, inserted the Python template, and saved `screenshots/workflow-transform-code-editor.png`.
