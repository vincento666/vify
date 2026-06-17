# Plan: Customer Assistant Sub-Agent Workbench Controls

## Slice 117.1

Add the smallest useful frontend surface for the backend harness: one operator-only control, one runtime helper, and one browser UAT path against seeded data.

## Approach

1. Add failing frontend API/runtime/panel contract tests.
2. Add typed frontend API methods for spawn and run detail.
3. Add runtime state for `subAgentRun` plus a `spawnCustomerAssistantRuntimeSubAgent` helper.
4. Add a compact control row to the existing progress panel to avoid creating another large card.
5. Extend/author a browser UAT script that opens a seeded story, launches the sub-agent, and asserts event/audit evidence appears.

## Test Strategy

- Focused unit: `frontend/src/api/customerAssistant.test.ts`, `frontend/src/views/customerAssistant/customerAssistantRuntime.test.ts`, `frontend/src/views/customerAssistant/customerAssistantPanel.test.ts`.
- Rem governance: include `frontend/src/remScaleClosure.test.ts` and
  `frontend/src/utils/remGovernance.test.ts` through the focused frontend
  command.
- Browser UAT: Playwright script under `frontend/e2e/` against `scripts/dev.sh` and seeded data.

## Risks

- Existing panel is dense; keep the UI compact and avoid new page sections.
- Background completion timing can vary; browser UAT should poll status/evidence.
- Later outbox/inbox slices will touch the same frontend area, so keep this patch narrow.
