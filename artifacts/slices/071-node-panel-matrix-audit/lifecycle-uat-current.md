## Workflow / Chatflow Lifecycle UAT

Date: 2026-06-08

Current lifecycle gates executed with local backend on `8000` and frontend on `5173`.

### Passed

- Workflow/chatflow canvas UX lifecycle
  - Evidence: `e2e-workflow-canvas-ux-lifecycle-current.txt`
  - Covers canvas save, auto-layout, condition edges, branch persistence, and chatflow guide question path.

- Workflow/chatflow list polish
  - Evidence: `e2e-workflow-chatflow-list-polish-current.txt`
  - Covers list page styling/copy, Chinese button labels, and workflow/chatflow naming.

- Chatflow trial chat panel
  - Evidence: `e2e-chatflow-trial-chat-panel-current.txt`
  - Covers chat-style test panel input/send behavior.

- Workflow publish/open-api/debug
  - Evidence: `e2e-workflow-publish-current.txt`
  - Covers publish gate, successful run status, publish confirmation, Open API and debug entry.

- Chatflow publish/open shell
  - Evidence: `e2e-chatflow-publish-after-close-fix.txt`
  - Covers publish gate modal, Open lifecycle tab, chat trial run, successful run status, and publish confirmation.

- Workflow toolbar zoom
  - Evidence: `e2e-workflow-toolbar-zoom-current.txt`
  - Covers zoom buttons/percentage interaction regression.

### Notes

- The first lifecycle run failed because the local frontend dev server was not running; the frontend was restarted before rerunning these gates.
- `chatflow-publish.mjs` was updated to use the current publish modal and chat-style trial-run panel.
