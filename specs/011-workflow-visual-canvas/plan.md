# Plan 011: Workflow Visual Canvas

## Architecture

- Add a reusable frontend flow builder under `frontend/src/views/workflow` and `frontend/src/components/workflow`.
- Use `@vue-flow/core` for pan/zoom/drag/connect behavior instead of hand-rolling canvas mechanics. Current compatible version checked by npm is `1.48.2`, with `vue` peer dependency `^3.3.0`.
- Keep backend graph contract compatible with current nodes/edges; store visual positions in `node.config.ui.position` for the first slice to avoid a schema migration.
- Add frontend graph adapter functions:
  - API detail -> canvas nodes/edges.
  - canvas graph -> API `nodes`/`edges`.
  - default graph -> START/END with safe positions.
- Add node metadata registry for current runtime node types.
- Add Coze-like custom node and edge renderers on top of Vue Flow. Do not use default Vue Flow node styling as the final UI.
- Keep node forms runtime-backed and small. Present Coze-like sections, but only expose the minimal fields supported by the current executor.
- Build variable catalog from START/global variables and connected upstream node output variables for the active node. The selector writes current `{{node.variable}}` templates so backend compatibility stays intact.
- Add shared parameter editors before broadening node-specific forms:
  - `VariableReferencePicker`
  - `NodeInputParameterEditor`
  - `NodeOutputParameterEditor`
  - Coze-style panel section renderer.
- Treat the LLM panel as the first full panel template: header, single-run behavior, model selector, skill shell, input rows, system/user prompt editors, and output rows.
- Defer batch mode, visual input, streaming/continue, exception handling, and editable model settings to later advanced slices.
- Build output parameter definitions before relying on downstream reference picker options.
- Apply basic input/output controls to all current nodes before implementing advanced fields.
- Add selected-node test as a separate action from full-flow test run. The node header run icon builds an editable fixture for required upstream inputs, runs only the selected node, and records node-only output/error evidence.
- Keep runtime execution in `007`; this spec calls existing run API and maps results to canvas state.
- Use Coze/HiAgent reference as product evidence. The current live Coze audit is `artifacts/research/coze-workflow/spec-011-015-live-audit-20260601.md`; when it conflicts with older screenshots, the live audit wins.

## UI Shape

- Header: back, icon/name, info/edit icons, status/autosave state, compact action icons, primary publish, and more menu. Do not reserve top banner height unless a future live reference reintroduces one.
- Left panel: workflow overview/resources only. The primary node-add affordance belongs in the bottom toolbar.
- Center: full-height dotted-grid canvas with Coze-like compact node cards, purple ports, curved edges, centered bottom toolbar, panel/view control, zoom dropdown, utility icon buttons, required visible operation-mode icon button for `触控板模式` / `鼠标模式` with tooltip/aria label, prominent add-node action, role/action shell, wrench/debug action, and green run/test action.
- Right panel: selected node config or workflow settings.
- Full-flow debug: bottom dock titled like `调试`, with run tree and detail/flamegraph area when run evidence exists.
- Selected-node test: launched from the right panel header run icon; fixture input may use a compact drawer as long as it does not replace the bottom debug panel.
- Bottom dock: wrench-toggleable debug/tools panel with validation/error list, run diagnostics/log placeholders, run tree/detail states, empty state, scroll area, and close action.

## Backend Notes

- Preserve `/api/v1/workflows` envelope.
- No DB schema migration required for first implementation unless positions need first-class columns later.
- `status=PUBLISHED` remains existing compatibility flag until release/version specs add immutable versions.

## Slice Order

011.1 -> 011.2 -> 011.3 -> 011.4 -> 011.5 -> 011.6 -> 011.7 -> 011.8 -> 011.9 -> 011.10 -> 011.11
