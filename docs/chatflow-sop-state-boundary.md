# Chatflow SOP State Boundary

Spec 216.3 finalizes the SOP Router boundary on runtime v2: runtime-lab
persists its own route ledger and child Chatflow refs, but does not persist
Chatflow execution state as a second source of truth.

## Persisted Runtime-Lab Ledger

`runtime_lab_session`

- `status`
- `active_task_id`
- `version`
- audit columns

`runtime_lab_task`

- `session_id`
- `sop_id`
- `status`
- `parent_task_id`
- `resume_summary`
- `chatflow_id`
- `chatflow_session_id`
- `chatflow_run_id`
- `chatflow_event_id`
- `chatflow_checkpoint_id`
- `runtime_version`
- `suspended_at`
- `completed_at`
- `expires_at`
- audit columns

`runtime_lab_event`

- append-only route and task history
- payloads do not carry child execution mirrors such as `currentStep`,
  `pendingPrompt`, `collected`, `scopedVariables`, `checkpoint`, `nodeEvents`,
  or `runStatus`

`runtime_lab_command`

- idempotent command replay payloads

## Removed Mirrors

Slice 213.3.5g removes:

- `runtime_lab_checkpoint`
- `runtime_lab_task.current_step`
- `runtime_lab_task.business_refs`
- repository checkpoint accessors
- `RuntimeLabService._session_business_context`
- module helper `_sop_checkpoint_from_row`
- public task payload keys `currentStep` and `businessRefs`

Slice 216.3 additionally removes:

- `runtime_lab_task.checkpoint_id`
- runtime-lab event payload `currentStep` mirrors
- aggregator task-step side channel APIs
- runtime-lab event / task-row fallbacks for current-step resolution

## Runtime Facts

Current step / waiting node source:

- Child Chatflow runtime result checkpoint `pendingNodeKey`.
- Direct fake-adapter tests may use an in-process synthetic child-runtime
  projection, but it is not persisted and is not exposed as RuntimeLab ledger.

Business context priority:

1. Child Chatflow `conversation` variables
2. Same-process adapter overlay populated from adapter results for tests and
   immediate in-process turns only

The aggregator no longer falls back to `task.business_refs`; that column is gone.

## Production Binding Boundary

Production runtime-lab bootstrap must use explicit SOP-to-Chatflow bindings.

- If `HIFY_RUNTIME_LAB_SOP_CHATFLOW_IDS` has no binding for a requested SOP,
  the adapter returns `MISSING_CHATFLOW_BINDING`.
- The runtime-lab web factory no longer injects `FakeSopRuntimeAdapter` as a
  production fallback.
- `FakeSopRuntimeAdapter` remains available for direct tests and explicit test
  fallback fixtures only.
- RuntimeLab child Chatflow LLM execution is controlled separately from route
  arbitration. `HIFY_RUNTIME_LAB_SOP_LLM_MODE=mock` is the default for ordinary
  offline RuntimeLab UAT and ignores stale live agents in the local DB;
  `HIFY_RUNTIME_LAB_SOP_LLM_MODE=live` explicitly enables provider-backed
  child Chatflow LLM nodes.

## Public API

`activeTask` and `suspendedTasks` expose runtime-lab ledger fields plus
`chatflowSession` refs. They no longer expose `currentStep`, `businessRefs`, or
root-level `checkpointId`.

Chatflow trace remains an aggregate view. It derives:

- runtime refs from `runtime_lab_task.chatflow_*`
- current step from child Chatflow runtime waiting checkpoint
- pending prompt from child Chatflow interrupt event / session output /
  checkpoint resume schema
- collected values from child Chatflow `conversation` variables
- scoped variables from child Chatflow checkpoint `variable_scopes`
- checkpoint from child Chatflow waiting checkpoint
- node events from child Chatflow runtime event stream
- run status from child Chatflow runtime run row
- sanitized RuntimeLab route ledger events with execution-state mirror keys
  removed from historical payloads

## Evidence

- RED: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3.5g/red.txt`
- Unit: `unit.txt`
- Contract: `contract.txt`
- Integration: `integration.txt`
- E2E: `e2e.txt`
- UAT: `uat.md`
- Production binding: `artifacts/slices/213-runtime-async-default-invocation-gateway/213.3.6/`
- 216.3 RED: `artifacts/slices/216-chatflow-sop-compat-on-dag/216.3/red.txt`
- 216.3 Unit: `artifacts/slices/216-chatflow-sop-compat-on-dag/216.3/unit.txt`
- 216.3 Integration: `artifacts/slices/216-chatflow-sop-compat-on-dag/216.3/integration.txt`
- 216.3 Contract: `artifacts/slices/216-chatflow-sop-compat-on-dag/216.3/contract.txt`
- 216.4 UAT: `artifacts/slices/216-chatflow-sop-compat-on-dag/216.4/uat.md`
