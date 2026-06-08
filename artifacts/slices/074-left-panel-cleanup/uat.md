# 074 Left Panel Cleanup UAT

## Browser UAT

- URL: `http://127.0.0.1:5173/chatflows/create`
- Viewport: `877x832` compact canvas
- Action: collapse left dialog settings panel, open trial-run panel from bottom toolbar.
- Expected: canvas remains visible, start/end nodes fit inside the available left canvas, bottom toolbar does not overlap the right trial-run panel.
- Result: PASS

## Screenshots

- `artifacts/slices/074-left-panel-cleanup/screenshots/collapse-failure-geometry.png`
- `artifacts/slices/074-left-panel-cleanup/screenshots/chatflow-collapse-toolbar.png`
