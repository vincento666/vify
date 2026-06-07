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

## 031.0 Spec Sign-off

Status: ready for adapter-contract implementation, now completed by 031.1
through 031.3.

Spec 031.0 is a documentation-only gate. It establishes the adapter-contract
scope between the isolated runtime control plane and future Chatflow SOP
integration. It does not introduce application code, tests, API behavior,
database schema, or runtime behavior.

Signed-off 031.0 boundaries:

- 031 defines the SOP adapter contract only.
- 031 proves the contract with a fake adapter.
- 031 keeps real Chatflow execution out of scope.
- 031 preserves one-way dependency: runtime-lab may define/call the adapter
  port, but Workflow/Chatflow must not import `runtime_lab`.
- 031 leaves real Chatflow SOP integration to 032.

031.0 evidence is stored under
`artifacts/slices/031-chatflow-sop-adapter-contract/031.0/`.

## 031 Completion Sign-off

Status: complete and ready for 032 boundary discovery.

Completed slices:

- 031.1 adapter port and DTOs;
- 031.2 runtime service adapter boundary;
- 031.3 dependency-direction gate.

Final signed-off boundaries:

- `SopRuntimeAdapter` is the adapter port for start, continue, suspend, and
  resume.
- `RuntimeLabService` routes selected SOP actions through the adapter port.
- Runtime task ledger remains the source of truth for task status, route
  events, idempotency, and resume policy.
- Adapter failures are normalized into runtime-safe `ERROR` events and safe
  user replies.
- Existing Workflow/Chatflow modules do not import `runtime_lab`.
- No real Chatflow execution is wired in 031.

Final evidence is stored under
`artifacts/slices/031-chatflow-sop-adapter-contract/031.3/`.
