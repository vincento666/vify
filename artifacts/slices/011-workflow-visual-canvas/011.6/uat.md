# 011.6 Browser UAT

## Scope

- Feature: publish guard, Open API shell, and observe shell.
- Goal: publish is blocked until validation and a current successful test run pass; after publish, author can inspect API invocation details and latest run status.

## Browser Evidence

- Browser interaction screenshot: `../../../../output/playwright/0116-workflow-publish.png`
- Current Codex in-app browser context remains captured under `../011.5/in-app-browser-current.png`.

## Acceptance

- Default disconnected canvas opens publish panel with `画布校验未通过`.
- Connected but untested canvas remains blocked with `需要先完成一次成功试运行`.
- A successful test run enables `确认发布`.
- Confirm publish updates workflow status to `PUBLISHED`.
- `Open API` tab shows `POST /api/v1/workflows/{id}/runs` and request sample fields.
- `运行观测` tab shows latest `Run ID`, `SUCCEEDED`, and output keys/payload.

## Gate Evidence

- RED: `red.txt`
- Unit: `unit-publish.txt`, `frontend-unit.txt`
- Build: `frontend-build.txt`
- Backend integration: `backend-integration.txt`
- E2E: `e2e.txt`
