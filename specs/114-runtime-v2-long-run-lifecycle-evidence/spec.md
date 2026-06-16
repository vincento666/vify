# Feature Spec: Runtime V2 Long-Run Lifecycle Evidence

## Status

Complete.

## User Story

As a demo operator relying on runtime v2 for long-running Workflow/Chatflow runs, I can query an interrupted run after the original client disconnects, resume it from its durable checkpoint, cancel a separate interrupted run, and trust that terminal state, events, and checkpoint evidence remain durable.

## Functional Requirements

- A runtime v2 run interrupted on a resumable node must be queryable through `GET /api/v1/runtime-runs/{run_id}` from a separate request/client.
- The query result must expose the active checkpoint needed to resume the run.
- `GET /api/v1/runtime-runs/{run_id}/events` must expose durable checkpoint IDs on checkpoint-bearing runtime v2 events.
- `POST /api/v1/runtime-runs/{run_id}/resume` must complete the interrupted run from the persisted checkpoint when called from a separate request/client.
- `POST /api/v1/runtime-runs/{run_id}/cancel` must mark a separate interrupted run `CANCELLED`, close its waiting checkpoint, and append a durable terminal cancellation event linked to the closed checkpoint.
- Event replay with `afterSequence` must continue to work after a separate request/client reconnects.

## Non-Goals

- New frontend controls or browser-visible workflow route changes.
- Customer-assistant runtime, seed data, live acceptance, MySQL, or provider-backed LLM/tool execution.
- Hard-stopping external processes beyond the existing cooperative runtime v2 cancellation lifecycle.
- Redesigning runtime v2 checkpoint storage.

## Acceptance Criteria

- RED evidence shows checkpoint-linked runtime v2 event replay is missing before implementation.
- Focused integration evidence proves an interrupted Chatflow runtime v2 run can be queried and resumed after a fresh client reconnects.
- Focused integration evidence proves a separate interrupted run can be cancelled after a fresh client reconnects.
- Resume and cancel terminal events retain checkpoint IDs, and the underlying checkpoint rows are completed rather than deleted.
- Focused runtime v2/workflow integration tests are green.
- Ruff is green if Python production code is touched.

## Evidence

Evidence lives under `artifacts/slices/114-runtime-v2-long-run-lifecycle-evidence/114.1/`.

- RED: `red.txt`
- Focused integration: `integration.txt`
- Runtime v2 facade regressions: `runtime-v2-facades.txt`
- Focused e2e: `e2e.txt`
- Ruff: `ruff.txt`
