# Spec 021: Coze Composer Run Debug Refactor

## Goal

Refactor Hify's current global `/observe` implementation into a Coze composer-style run debugging experience. This spec follows the non-evaluation Coze Studio product logic, not Coze Loop.

In Coze Studio, workflow and chatflow execution debugging is anchored to the composer/build page. External workflow/chatflow API calls return a `debug_url` that opens the workflow page with an execution identifier so users can inspect that specific run's node inputs, outputs, errors, and execution details. It is not a separate top-level Observability product module.

021 turns Hify's observe surfaces into embedded run detail panels inside Workflow, Chatflow, and Agent authoring/debug pages, while keeping optional deep-link routes for external API/debug URL entry.

## Product Boundary

- Remove `观测` as a top-level sidebar/navigation entry for the Coze composer product mode.
- Do not put Observe inside Evaluation.
- Keep Evaluation and run debugging as separate concerns:
  - Evaluation answers whether a target version performs well.
  - Run debugging answers what happened during one concrete Workflow/Chatflow/Agent execution.
- Preserve the existing backend observe data where useful, but expose it through composer run-detail APIs and embedded panels.
- Use deep links to route users back to the owning composer page, not to an independent `/observe` destination.
- Keep Coze Loop-style SDK trace ingestion, Prompt Trace, and platform-wide trace analytics out of scope.

## Evidence Baseline

Coze Studio API reference behavior:

- Workflow execution returns `debug_url`.
- `debug_url` points to a workflow build/debug page with `execute_id`, `space_id`, and `workflow_id`.
- The page is used to view execution results and each workflow node's input/output.
- Chatflow streaming completion also returns `debug_url`.
- Chatflow `debug_url` opens a visual test-run interface with node input/output details for online debugging and troubleshooting.

Local Hify evidence:

- 011 and 012 already introduced canvas bottom debug docks and run panels.
- 014 already introduced Agent Workbench preview/debug detail panel with call tree and flame view.
- 019 introduced `/observe` as a global route and observe APIs, but that was based on a broader publish/observe interpretation.

021 corrects the product IA for Coze composer mode.

## Current Hify State

Currently:

- `/observe` is a top-level page.
- Sidebar includes `观测`.
- `frontend/src/views/workflow/ObserveDashboard.vue` renders a global observe dashboard.
- `app/modules/observe/` exposes `/api/v1/observe/*`.
- Workflow canvas has debug dock and a `查看观测详情` link that navigates to `/observe?runId=...`.
- Agent Workbench preview debug panel already keeps debug detail in-place.

The current shape creates product duplication:

- Workflow/Chatflow already have debug dock surfaces.
- Agent already has preview debug detail.
- `/observe` repeats run detail outside the owning authoring page.
- Users must leave the canvas/workbench even when the needed call tree, flamegraph, and node detail could be shown in-place.

## Target Product Model

### Workflow

Workflow canvas owns workflow run debugging.

Required behavior:

- Trial run and published/API execution detail open inside the Workflow canvas debug dock.
- Deep link format routes back to canvas:
  - `/workflows/{workflowId}/canvas?runId={runId}&debug=1`
  - `/workflows/{workflowId}/canvas?executeId={executeId}&debug=1`
- Debug panel shows:
  - run status, latency, start/end time;
  - call tree;
  - flamegraph/timeline;
  - node detail;
  - node input/output;
  - resource/tool/subworkflow calls;
  - raw event payload in advanced disclosure;
  - errors and retry/failure reason.

### Chatflow

Chatflow canvas owns chatflow run debugging.

Required behavior:

- Trial run, interrupted/resumed conversation runs, and published channel/API runs open inside the Chatflow debug dock.
- Deep link format routes back to canvas:
  - `/chatflows/{chatflowId}/canvas?runId={runId}&debug=1`
  - `/chatflows/{chatflowId}/canvas?executeId={executeId}&debug=1`
- Debug panel shows:
  - conversation/session identity;
  - channel/user/conversation variables;
  - waiting/interrupted node state;
  - resumed event sequence;
  - call tree and flamegraph;
  - node input/output and errors.

### Agent Workbench

Agent Workbench owns agent preview run debugging.

Required behavior:

- Preview debug detail remains embedded in the Agent Workbench.
- Deep link format routes back to the Workbench:
  - `/agents/{agentId}/workbench?previewRunId={runId}&debug=1`
- If an Agent run invokes Workflow, Chatflow, MCP, RAG, or tools, the debug detail shows the nested call tree and allows opening the owning Workflow/Chatflow canvas when appropriate.

### External Debug URL

External API execution can still return a debug URL, but it must be a composer deep link:

- Workflow API returns a canvas deep link.
- Chatflow API returns a canvas deep link.
- Agent preview/API debug returns a Workbench deep link where applicable.

The deep link must auto-open the debug panel and select the requested run.

## Non-Goals

- No standalone top-level `/observe` navigation.
- No Coze Loop Trace module.
- No SDK trace ingestion platform.
- No Prompt Trace or Prompt Engineering module.
- No Evaluation-owned observe panel.
- No duplicated run-detail page that forces users away from the owning composer surface.

## Slices

| Slice | Behavior | Acceptance Gates |
|------|----------|------------------|
| 021.1 IA cleanup and route contract | Remove top-level Observe nav and define composer deep-link contract | RED: nav/route tests fail; Unit: route helper; E2E: sidebar has no Observe; UAT: no top-level observe entry |
| 021.2 Workflow embedded run detail | Workflow canvas loads runId/executeId and opens debug dock with call tree/flamegraph/node detail | RED: workflow deep-link E2E fails; Integration: run detail by workflow; E2E: run -> deep link -> debug dock; UAT: no `/observe` jump |
| 021.3 Chatflow embedded run detail | Chatflow canvas loads interrupted/resumed/channel runs into debug dock | RED: chatflow deep-link E2E fails; Integration: session run detail; E2E: interrupt/resume -> deep link; UAT: event timeline and variables visible |
| 021.4 Agent preview embedded run detail | Agent Workbench deep links preview run and keeps fourth debug panel in-place | RED: workbench deep-link test fails; Unit: debug panel state; E2E: preview -> reload deep link; UAT: panel focused and columns not squeezed |
| 021.5 Debug URL API compatibility | Published Workflow/Chatflow/API execution returns composer debug URLs | RED: API debug_url contract fails; Integration: workflow/chatflow APIs; E2E: open returned debug_url; UAT: URL opens owning canvas/workbench |
| 021.6 Retire standalone observe surface | Keep backend data adapters but remove global observe page as user-facing product entry | RED: old observe navigation E2E fails intentionally; Integration: existing observe data still queryable through composer adapters; E2E: debug dock replaces observe link; UAT: no product duplication |
| 021.12 Publish/Open API/debug IA regression | Split publish, Open API, and run-debug into non-overlapping composer surfaces; `开放` has exactly one tab surface | RED: canvas IA E2E fails while `观测` opens an ops panel and `统计` is active; Unit: tab/modal/debug state; E2E: publish modal, Open API tab, debug dock; UAT: no duplicate ops/observe/publish checks |

## Slice Evidence

- 021.12 evidence: `artifacts/slices/021-coze-composer-run-debug-refactor/021.12-publish-open-debug-ia/`
  - RED: `red-unit.txt`, `red-e2e.txt`
  - Unit/rem: `unit.txt`, `rem-scale.txt`
  - Integration/contract: `integration.txt`
  - Build: `build.txt`
  - E2E: `e2e-composer-ia.txt`, `e2e-workflow-publish.txt`, `e2e-chatflow-publish.txt`, `e2e-chatflow-channels.txt`, `e2e-run-panel-cleanup.txt`
  - Browser UAT: `uat.md`, `screenshots/browser-uat-workflow.png`, `screenshots/browser-uat-chatflow.png`

## Evidence

Each slice must save evidence under:

```text
artifacts/slices/021-coze-composer-run-debug-refactor/{slice-id}/
├── red.txt
├── unit.txt
├── integration.txt
├── e2e.txt
├── uat.md
└── screenshots/
```

## Done Criteria

021 is done when:

- `观测` is no longer a top-level product entry in Coze composer mode.
- Workflow/Chatflow/Agent each own their run-debug detail in-place.
- Existing call tree/flamegraph/node detail capabilities are preserved.
- API/debug URL flows return to the owning composer page and auto-open the selected run.
- Evaluation can link to run debug detail without owning or embedding Observe.
- Browser UAT proves users do not need to jump to a separate `/observe` page for ordinary Workflow/Chatflow/Agent debugging.
