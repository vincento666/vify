# Spec 031: Chatflow SOP Adapter Contract

## Goal

Define the one-way adapter contract that allows the isolated runtime control
plane to start, continue, suspend, and resume a SOP backed by existing Chatflow
runtime APIs.

031 defines the contract and proves it with fakes. It does not connect real
Chatflow execution yet.

## Dependency

031 starts only after 030 gates pass.

Required 030 capabilities:

- finite candidate recall;
- constrained arbitration;
- policy gate;
- active-SOP conservative routing behavior;
- stable runtime-lab debug evidence.

## Boundary

In scope:

- adapter port/interface for SOP execution;
- request and response DTOs;
- checkpoint mapping contract;
- variable snapshot contract;
- error and retry semantics;
- fake adapter implementation for tests;
- contract tests proving runtime can call the port without depending on
  concrete Chatflow internals.

Out of scope:

- real Chatflow repository or engine calls;
- frontend UI;
- semantic routing changes;
- FAQ/RAG/Agent/handoff policy;
- production API renaming.

## One-Way Dependency Rule

The runtime router may call an adapter port. Existing Workflow/Chatflow modules
must not import `runtime_lab`.

The preferred shape is:

```text
runtime_lab domain
  -> SopRuntimeAdapter port
  -> fake adapter in 031 tests
  -> real Chatflow adapter in 032
```

031 must not create a reverse dependency from Chatflow into runtime-lab.

## Adapter Contract

Required operations:

- `start_sop(request) -> SopExecutionResult`
- `continue_sop(request) -> SopExecutionResult`
- `suspend_sop(request) -> SopCheckpoint`
- `resume_sop(request) -> SopExecutionResult`

Required request fields:

- `runtime_session_id`
- `runtime_task_id`
- `sop_id`
- `message`
- `checkpoint`
- `collected`
- `business_refs`
- `metadata`

Required result fields:

- `status`: `WAITING`, `COMPLETED`, `FAILED`
- `current_step`
- `reply`
- `pending_prompt`
- `checkpoint`
- `collected`
- `business_refs`
- `events`
- `error`

The adapter returns normalized SOP state. The runtime ledger remains the source
of truth for task status, route events, idempotency, and resume policy.

## Checkpoint Contract

The checkpoint must be serializable and safe to store in the runtime ledger.

Minimum fields:

- `sop_runtime_id`
- `current_node_id`
- `current_step`
- `pending_prompt`
- `collected`
- `scoped_variables`
- `version`

031 must document which fields are mandatory now and which are reserved for the
real Chatflow adapter in 032.

## Acceptance Criteria

- Runtime service can use the adapter port with a fake SOP adapter.
- Adapter errors are normalized into runtime-safe failure responses.
- Checkpoint payloads are serializable and do not contain secrets.
- One-way dependency is preserved.
- No real Chatflow code is called.
- Existing 029 and 030 gates still pass.

## Completion Gate

031 is complete only when:

- adapter port and DTO tests pass;
- runtime integration tests pass with the fake adapter;
- dependency-direction check passes or is manually documented;
- evidence is saved under
  `artifacts/slices/031-chatflow-sop-adapter-contract/`;
- one git commit contains only 031 changes.
