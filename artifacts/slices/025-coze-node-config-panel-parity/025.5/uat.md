# 025.5 Browser UAT

Date: 2026-06-05

Targets:

- Chatflow: `http://127.0.0.1:5173/chatflows/1727/canvas?debug=1&runId=1395`
- Workflow: `http://127.0.0.1:5173/workflows/1728/canvas?debug=1&runId=1396`

Verified:

- Chatflow waiting node keeps the incoming edge animated with `edge-running`.
- The next edge after the waiting node remains normal and does not animate.
- Workflow condition run marks `router->vip` with `edge-active-branch`.
- Workflow condition run marks `router->fallback` with `edge-inactive-branch`.
- Inactive sibling branch does not receive `edge-running`.

Screenshots:

- `screenshots/uat-running-edge.png`
- `screenshots/uat-active-branch.png`

State evidence:

- `uat-browser.json`
