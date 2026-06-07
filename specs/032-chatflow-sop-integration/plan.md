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
