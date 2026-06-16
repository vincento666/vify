# Plan 067: Cross-runtime Observability And Regression Gate

## Event Summary

Normalize visible event summaries:

```text
assistant event -> task progress
worker event -> worker progress
chatflow event -> SOP/runtime progress
workflow event -> canvas runtime progress
```

Keep raw refs available for debug.

Every visible summary should include correlation refs when available:

- assistant run id;
- task id;
- worker run id;
- runtime run id;
- source event id/sequence.

Label entries as live, replay, or compatibility summary.

## Canvas Debug Projection

Workflow/Chatflow canvas debug surfaces must render from runtime v2 state:

- `PENDING`: neutral node state;
- `RUNNING`: running animation;
- `WAITING`: interrupted/waiting visual state;
- `COMPLETED`: completed node state;
- `FAILED`: failed node state and stopped run;
- `SKIPPED`: skipped branch state.

Debug panel rows update from the same events. Reconnect must replay durable
events and restore node states without inventing frontend-only progress.

## Regression Matrix

Cover:

- legacy customer assistant turn;
- harness spawn-sub-agent;
- worker async pending/completed/failure;
- Chatflow v2 compatible graph;
- Chatflow v1 fallback graph;
- SOP multi-level router calling Chatflow v2 and v1 fallback in one session;
- Workflow v2 supported graph if enabled.
- Chatflow canvas debug live node status and node failure stop;
- Workflow canvas debug live node status and node failure stop if enabled.

## UAT

Browser UAT must record:

- task ledger;
- worker refs;
- runtime refs;
- event timeline;
- canvas node animation/completed/waiting/failed states;
- debug panel real-time node rows;
- warnings/fallback reasons.
- timeout/cancel/failure states;
- latency/status/fallback summary artifacts.
- SOP router context: `sop_key`, `route_id`, `route_turn_id`, `intent_key`,
  `task_id`, and `session_id`.
