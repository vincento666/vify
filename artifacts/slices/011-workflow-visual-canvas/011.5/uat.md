# 011.5 Browser UAT

## Scope

- Feature: workflow canvas validation and test run panel.
- Goal: invalid graph blocks run with visible errors; valid graph saves and calls backend `/runs`, then displays the returned status/output.

## Browser Evidence

- In-app Codex browser current canvas capture: `in-app-browser-current.png`
- In-app Codex browser after navigation-control attempt: `in-app-browser-after-nav-attempt.png`
- Interaction screenshot from the browser e2e run: `../../../../output/playwright/0115-workflow-test-run.png`

The current Codex in-app browser shows the local Hify canvas with the same dotted workbench, node cards, connection ports, bottom zoom toolbar, and bottom-right `+ 添加节点` affordance used as the Coze-aligned target. Direct in-app control was blocked by macOS Accessibility permission, so the interactive UAT path was executed through the browser e2e runner against the same local app URL.

## Acceptance

- Invalid default START/END graph opens `试运行` panel and displays `START must connect to END through at least one path`.
- `快速连线` converts the graph into a runnable START -> END flow.
- Clicking `运行` persists the canvas and calls `/api/v1/workflows/{id}/runs`.
- Result panel displays `status: SUCCEEDED` and an `output` payload from the backend response.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-validation.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend integration: `backend-integration.txt`
- E2E: `e2e.txt`
