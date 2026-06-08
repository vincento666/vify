# 068 Transform Nodes Runtime

## Scope

- Adds minimal runtime executors for `CODE`, `TEXT_PROCESS`, and `JSON_PARSE`.
- Keeps the `CODE` node intentionally technical and restricted to a small safe Python execution surface.
- Covers workflow runtime, chatflow runtime, JSON parse failure reporting, frontend node/panel exposure, and browser UAT.
- The staged `engine.py` diff is intentionally index-only and limited to transform nodes; unrelated workflow runtime dirty work remains unstaged.

## Gates

- Staged Python syntax: `staged-py-compile.txt`.
- Backend focused: `test_transform_nodes.py`, 3 tests passed.
- Frontend focused/REM: `flowGraph.test.ts`, `nodeConfig.test.ts`, and `remScaleClosure.test.ts`, 37 tests passed.
- Frontend full unit: 58 files / 192 tests passed.
- Frontend build: passed.
- E2E: `workflow-transform-nodes.mjs` passed.
- Browser UAT:
  - created workflow `5900`;
  - `CODE`, `TEXT_PROCESS`, and `JSON_PARSE` cards rendered;
  - JSON parse config panel rendered structured field mapping editor;
  - JSON parse config panel rendered 3 mapping rows.

## Screenshots

- `screenshots/transform-nodes.png`
- `screenshots/browser-uat-transform-canvas.png`
- `screenshots/browser-uat-json-panel.png`
