# Spec 065: Hify Workflow Runtime V2 Facade MVP

## Goal

Add a Hify Workflow runtime v2 facade over the shared runtime v2 core.

This brings Hify `flow_type=WORKFLOW` into the same run/status/event/result
contract as Chatflow v2 without adding Chatflow-specific session semantics.

## Dependency

065 depends on:

- 062 Hify Workflow/Chatflow shared runtime v2 core;
- 064 Hify runtime v2 core node coverage pack 1;
- 060 MySQL 8 migration strategy if the active target database is MySQL.

## Product Boundary

In scope:

- v2 run endpoint or explicit v2 mode for Hify Workflow;
- status/result/event refs;
- live event stream for supported Workflow graphs;
- Workflow canvas/debug run projection over runtime v2 node status/events;
- graph-level compatibility checker;
- preservation of caller context from external routers if a Workflow run is
  called by a routing layer;
- legacy Workflow run endpoint compatibility.

Out of scope:

- Chatflow session/checkpoint behavior;
- full replacement of existing Workflow endpoints;
- LLM/tool/API/agent/nested/code nodes beyond 064 coverage;
- WebSocket/Redis;
- external workflow frameworks.

## Hard Constraints

- This spec is for Hify's own Workflow module only.
- Workflow facade must use the shared runtime core from 062.
- Unsupported graphs must not partially execute as mixed v1/v2.
- Legacy `/api/v1/workflows/{id}/runs` response shape must remain compatible.
- Workflow v2 runs must use a stable published/snapshot workflow definition;
  draft edits must not change an in-flight run.
- Workflow facade must not depend on Chatflow session/checkpoint tables or
  Chatflow-specific conversation semantics.
- Runtime create requests should be idempotent when a request key is supplied.
- Workflow v2 live events must be projections over the shared runtime event
  store.
- Workflow debug run UI must consume runtime v2 async refs/status/events instead
  of a synchronous completion-time replay when v2 mode is selected.
- Workflow runtime v2 must preserve external router caller context where
  supplied, but must not become the owner of SOP multi-level routing.

## Acceptance Criteria

- A supported Hify Workflow graph can run through v2 and emit durable events.
- Status/result/events refs are fetchable.
- Pre-terminal node events are observable.
- Workflow debug panel receives real-time node status updates while the run is
  active.
- Node running/completed/waiting/failed visual states match runtime v2 node
  statuses.
- A node error stops the Workflow v2 run and updates the debug panel to failed.
- Workflow version/snapshot used by the run is recorded.
- Unsupported Workflow graphs produce clear unsupported reports or full-run
  fallback.
- Legacy Workflow run tests remain green.

## MVP Exit

065 is complete when Hify Workflow has a v2 facade using the same shared core as
Chatflow v2 for supported deterministic graphs.
