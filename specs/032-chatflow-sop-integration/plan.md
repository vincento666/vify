# Plan 032: Chatflow SOP Integration

## Architecture

Implement the real adapter behind the 031 port.

```text
runtime_lab RuntimeService
  -> SopRuntimeAdapter port
  -> ChatflowSopRuntimeAdapter
  -> existing Chatflow service/repository APIs
```

The adapter is the only integration layer. It should be replaceable without
changing route arbitration or task-ledger logic.

## Discovery First

Before implementation, inspect:

- current Chatflow run API;
- current Chatflow resume/session-state API;
- current checkpoint/event model from spec 018;
- existing tests for Chatflow conversation run and resume reliability.

If the existing Chatflow boundary cannot support one-way adapter calls, update
031 first instead of forcing integration here.

Discovery result:

- current Chatflow run/resume/session-state APIs are sufficient for one narrow
  real SOP adapter path;
- 032 should use `WorkflowService` directly rather than calling HTTP endpoints;
- `suspend_sop` should preserve an existing waiting checkpoint rather than
  inventing an arbitrary pause capability;
- if the adapter cannot find a waiting checkpoint for suspend/resume, it should
  return a normalized failure result;
- the first fixture should use an interruptible Chatflow shape such as
  `START -> INFORMATION_COLLECTION(order_no) -> QUESTION(confirm) -> END`.

## Test Strategy

RED tests first:

- adapter start against real Chatflow fixture;
- adapter continue;
- adapter suspend checkpoint mapping;
- adapter resume;
- runtime service E2E through adapter;
- dependency-direction architecture test.

Regression tests:

- existing runtime-lab mock path;
- existing Chatflow run/resume tests.

Implementation sequence:

```text
032.2 RED adapter tests
  -> 032.3 ChatflowSopRuntimeAdapter
  -> 032.4 runtime-lab API E2E
```

Do not start 032.3 until the 032.2 RED output has been captured.

## Evidence

Use:

```text
artifacts/slices/032-chatflow-sop-integration/
  032.0/
  032.1/
  ...
```

No frontend or browser UAT is required unless 032 changes user-visible frontend
behavior.

## Non-Goals

Do not:

- connect multiple SOPs before the first path passes;
- change route arbitration thresholds;
- add FAQ/RAG/Agent/handoff;
- expose a final `/chat` or `/query` API.
