# Plan 021: Coze Composer Run Debug Refactor

## Architecture Approach

021 is primarily an information architecture and routing refactor. It should reuse existing runtime evidence from Workflow, Chatflow, Agent preview, and the existing observe module instead of inventing a new telemetry backend.

The direction is:

- Keep run evidence collection where it already exists.
- Introduce composer-owned run detail facades.
- Move user-facing run detail UI into the owning composer surfaces.
- Convert `debug_url` into a deep link that opens the owning composer page and selected run detail.
- Remove global Observe from navigation and user flows.

## Backend Direction

Preserve existing observe data model and query service where useful, but add composer-facing facades:

- Workflow run detail:
  - `GET /api/v1/workflows/{workflow_id}/runs/{run_id}/debug`
  - optional `GET /api/v1/workflows/{workflow_id}/runs/by-execute/{execute_id}/debug`
- Chatflow run detail:
  - `GET /api/v1/chatflows/{chatflow_id}/runs/{run_id}/debug`
  - optional `GET /api/v1/chatflows/{chatflow_id}/runs/by-execute/{execute_id}/debug`
- Agent preview run detail:
  - `GET /api/v1/agents/{agent_id}/preview-runs/{run_id}/debug`

The response shape should be shared where possible:

```json
{
  "runId": 123,
  "ownerType": "WORKFLOW",
  "ownerId": 456,
  "status": "SUCCEEDED",
  "startedAt": "...",
  "finishedAt": "...",
  "elapsedMs": 321,
  "input": {},
  "output": {},
  "events": [],
  "callTree": [],
  "flamegraph": [],
  "nodeDetails": []
}
```

Keep `/api/v1/observe/*` temporarily for backward compatibility until all user-facing routes and E2E are migrated. Do not add it as a product entry.

## Frontend Direction

### Navigation

- Remove `观测` from `frontend/src/App.vue` sidebar.
- Keep `/observe` route only as a temporary compatibility route if needed, preferably redirecting to a composer deep link when `runId` has enough ownership metadata.

### Workflow / Chatflow Canvas

Use the existing bottom debug dock as the product home for run detail:

- On route query `debug=1&runId=...`, load run detail and open the dock.
- On route query `debug=1&executeId=...`, resolve execute ID to run detail and open the dock.
- Replace `查看观测详情` with `查看运行详情` or equivalent in-canvas action.
- Do not navigate to `/observe`.

### Publish / Open / Debug Composer IA

- Keep lifecycle tabs to `编排` and `开放` until the statistics product has a real surface.
- Render Open API/channel integration in the center `开放` surface only.
- Render publish checks, draft/published state, version metadata, confirm publish, version history, and rollback in a publish dialog.
- Use `调试详情` for run debugging and route it to the existing bottom debug dock.
- Do not render a mixed right-side `发布与运维` panel or a `运行观测` tab.

### Agent Workbench

Use the existing preview debug detail panel:

- On query `debug=1&previewRunId=...`, open the panel and select that preview run.
- Keep fourth-column horizontal-scroll behavior from 014.
- Nested Workflow/Chatflow invocations can expose secondary links to the owning canvas.

## Deep-Link Contract

Canonical links:

- Workflow: `/workflows/{id}/canvas?runId={runId}&debug=1`
- Workflow by execute ID: `/workflows/{id}/canvas?executeId={executeId}&debug=1`
- Chatflow: `/chatflows/{id}/canvas?runId={runId}&debug=1`
- Chatflow by execute ID: `/chatflows/{id}/canvas?executeId={executeId}&debug=1`
- Agent preview: `/agents/{id}/workbench?previewRunId={runId}&debug=1`

External API execution should return these URLs in `debugUrl` / `debug_url`.

## Testing Strategy

Every slice follows the existing high-spec gate:

- RED evidence first.
- Unit tests for URL helpers and debug-state reducers.
- Integration tests for composer run-detail endpoints and debug URL generation.
- E2E tests for browser-visible routes and panels.
- Browser UAT for Workflow, Chatflow, and Agent surfaces.

Run-detail tests must assert:

- The user remains on the owning composer page.
- The debug panel is open.
- The selected run ID or execute ID is visible.
- Call tree and flamegraph are populated from real run data.
- Node input/output and error details are visible where applicable.

## Migration Strategy

1. Add composer debug URL helpers while keeping old observe routes intact.
2. Move Workflow debug link from `/observe?runId=...` to canvas deep link.
3. Move Chatflow debug link similarly.
4. Wire Agent preview deep link.
5. Remove top-level Observe nav.
6. Convert or retire standalone `/observe` page after composer paths pass.

## Risks

- Existing tests may rely on `/observe`; migrate tests slice-by-slice instead of deleting all at once.
- Run ownership may be ambiguous if only `runId` is available. Add owner metadata or resolve from backend.
- Duplicating call tree/flamegraph components can cause drift. Prefer shared debug panel components.
- External debug URLs must not leak sensitive payloads. They should contain IDs only, not raw inputs.

## Dependencies

- 011 Workflow visual canvas and bottom debug dock.
- 012 Chatflow visual canvas and debug dock.
- 014 Agent Workbench preview/debug panel.
- 017 resource/tool/subworkflow evidence.
- 018 chatflow session state and event timeline.
- 019 observe data and run/session/handoff evidence.

## Done Criteria

021 is done when:

- Users can debug Workflow, Chatflow, and Agent runs without opening `/observe`.
- External API debug URLs return to the correct composer page.
- Existing call tree/flamegraph/node detail capability is preserved in embedded panels.
- Sidebar/top-level navigation no longer presents Observe as a separate product module.
- Backward-compatible observe data access is either safely retained internally or explicitly redirected.
- 021.12 publish/open/debug IA gate passes with evidence under `artifacts/slices/021-coze-composer-run-debug-refactor/021.12-publish-open-debug-ia/`.
