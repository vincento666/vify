# Plan 011: Workflow Visual Canvas

## Architecture

- Add a reusable frontend flow builder under `frontend/src/views/workflow` and `frontend/src/components/workflow`.
- Prefer `@vue-flow/core` for pan/zoom/drag/connect behavior instead of hand-rolling canvas mechanics.
- Keep backend graph contract compatible with current nodes/edges; store visual positions in `node.config.ui.position` for the first slice to avoid a schema migration.
- Add frontend graph adapter functions:
  - API detail -> canvas nodes/edges.
  - canvas graph -> API `nodes`/`edges`.
  - default graph -> START/END with safe positions.
- Add node metadata registry for current runtime node types.
- Keep runtime execution in `007`; this spec calls existing run API and maps results to canvas state.
- Use Coze/HiAgent reference as product evidence, but do not block implementation on logged-in Coze access once public docs and current screenshot gate are recorded.

## UI Shape

- Header: back, name, status, save state, tabs, validate, test run, publish.
- Left panel: node palette and workflow resources.
- Center: full-height canvas with grid, minimap/zoom controls, fit view, undo/redo later.
- Right panel: selected node config or workflow settings.
- Bottom/right drawer: test run input/result and node run details.

## Backend Notes

- Preserve `/api/v1/workflows` envelope.
- No DB schema migration required for first implementation unless positions need first-class columns later.
- `status=PUBLISHED` remains existing compatibility flag until release/version specs add immutable versions.

## Slice Order

011.1 -> 011.2 -> 011.3 -> 011.4 -> 011.5
