# Spec 062: Hify Workflow/Chatflow Shared Runtime V2 Core

## Goal

Create the shared runtime v2 core for Hify's own Workflow and Chatflow modules.

This is not an external workflow framework. It is the shared execution,
status/result, and event infrastructure under Hify `flow_type=WORKFLOW` and
`flow_type=CHATFLOW`.

## Dependency

062 depends on:

- 053 Workflow/Chatflow runtime v2 event alignment;
- 058 Chatflow runtime v2 spike evidence;
- 060 MySQL 8 migration strategy for runtime persistence, or an explicitly
  documented temporary SQLite strategy.

## Product Boundary

In scope:

- shared runtime run/status/result contract;
- shared node-run status contract for canvas/debug projections;
- generic runtime event store or `workflow_run_event`;
- event sequence strategy suitable for MySQL 8;
- runtime event envelope aligned with 053;
- event sink interface for Hify graph execution;
- caller context metadata required by external SOP routing layers;
- graph-level compatibility checker;
- compatibility boundaries for existing sync endpoints.

Out of scope:

- broad node coverage;
- Chatflow-specific facade behavior;
- Workflow facade product endpoint rollout;
- WebSocket/Redis;
- replacing old endpoints.

## Hard Constraints

- The core must serve both Hify Workflow and Hify Chatflow facades.
- Do not create a Chatflow-only runtime island.
- Do not do node-level v1/v2 mixed execution in this spec.
- Unsupported graphs must be rejected or fall back as a whole run.
- Existing Workflow/Chatflow APIs must remain compatible.
- Runtime events are the source of truth; SSE streams, list endpoints, and UI
  timelines are projections over persisted events.
- Canvas/debug run state must be a projection of runtime v2 run/node status and
  events, not a separate frontend-only state machine.
- Runtime creation/resume must be idempotent for a stable request key.
- Runtime event payloads must be schema-versioned and redacted.
- Runtime v2 must not replace the existing SOP multi-level router. It only
  preserves caller context and execution refs so the router can continue
  selecting, switching, suspending, resuming, and falling back across intents.

## Runner And Persistence Boundary

The shared runtime v2 core must define the execution boundary used by both Hify
Workflow and Hify Chatflow:

- background execution uses an independent database session or unit of work;
- request-scoped sessions must not be held after the request returns;
- terminal run status transitions are monotonic;
- node status transitions are monotonic for terminal states;
- resume attempts are recorded with attempt metadata, even if the first MVP only
  supports a narrow resume path;
- a node failure stops downstream scheduling and marks the run failed unless the
  graph has an explicitly supported error/fallback edge;
- cancellation is either implemented or explicitly represented as unsupported;
- event ordering is unique per run and safe for the active database strategy.

## Acceptance Criteria

- Shared runtime event envelope is implemented or specified with persistence.
- Shared node status model supports canvas/debug projection states:
  `PENDING`, `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, `SKIPPED`.
- Runtime create/resume requests are idempotent.
- Event sequence strategy is tested or explicitly limited to a single-process
  prototype.
- Runtime refs can represent owner type `WORKFLOW` and `CHATFLOW`.
- Compatibility checker reports unsupported nodes/edges.
- Runtime refs/events preserve SOP router caller context without depending on
  Chatflow-only storage.
- Node status/event refs are sufficient for canvas running animation,
  completion state, waiting state, and error state.
- A failed node stops the run and emits terminal failure evidence unless an
  explicit supported error path is configured.
- Background execution is proven not to depend on request-scoped sessions.
- No legacy endpoint behavior is broken.

## MVP Exit

062 is complete when Hify has a shared runtime v2 core foundation that later
Chatflow and Workflow facades can both use.
