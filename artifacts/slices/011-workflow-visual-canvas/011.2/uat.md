# 011.2 Canvas Graph Editor Gate

## RED

- `red.txt`
- Verified the graph save/reopen test failed because the canvas graph model did not exist.

## Unit

- `unit-graph.txt`
- `frontend-unit.txt`
- Verified default START/END graph, add node, move/drag persistence, connect, delete, serialize, and reopen hydration.

## Integration

- `backend-integration.txt`
- Verified existing Workflow graph CRUD remains compatible with position data stored under `config.ui.position`.

## E2E

- `e2e.txt`
- Browser automation created a workflow through the canvas, opened the add-node palette, added an LLM node, dragged it, connected the graph, saved it, and reopened `/workflows/{id}/canvas`.
- Screenshot: `output/playwright/0112-workflow-canvas.png`

## Browser UAT

- Codex in-app Browser reference from real Coze canvas:
  - `artifacts/research/coze-workflow/in-app-coze-chatflow-canvas-pane.png`
- Codex in-app Browser local UAT:
  - `in-app-browser-uat.png`
  - `in-app-browser-uat-add-menu.png`
- User-visible result: local Workflow canvas shows the Coze-like dotted canvas, compact START/END node cards, centered bottom toolbar, and bottom-right `+ 添加节点` palette.
