# 105 Workflow/Chatflow Lifecycle Current Gate

- Date: 2026-06-09
- Scope: workflow/chatflow lifecycle surfaces: canvas UX, list pages, toolbar zoom, trial run, publish/open/debug.

## RED

- `e2e-chatflow-publish.txt` failed because the test waited for any assistant bubble; the chatflow welcome opening message matched that condition before the actual trial run status settled.

## Fix

- `frontend/e2e/chatflow-publish.mjs` now waits for the chatflow trial run meta status `SUCCEEDED` before opening the publish dialog.

## Evidence

- `e2e-workflow-canvas-ux-lifecycle.txt`: workflow/chatflow canvas lifecycle passes.
- `e2e-list-polish.txt`: workflow/chatflow list polish passes.
- `e2e-toolbar-zoom.txt`: toolbar zoom passes.
- `e2e-chatflow-trial-chat-panel.txt`: chatflow trial chat panel passes.
- `e2e-workflow-publish.txt`: workflow publish/open/debug passes.
- `e2e-chatflow-publish-after-wait-fix.txt`: chatflow publish/open shell passes after the wait fix.

## Result

Lifecycle gates pass for the covered workflow/chatflow paths.
