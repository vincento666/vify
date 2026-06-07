# Plan 031: Chatflow SOP Adapter Contract

## Architecture

Introduce a SOP adapter port at the runtime boundary. The runtime continues to
own route control, persistence, idempotency, and task ledger state.

The adapter owns only SOP execution semantics:

- start;
- continue;
- suspend checkpoint creation;
- resume from checkpoint;
- normalized reply and collected variables.

## Suggested Files

```text
app/modules/runtime_lab/domain/sop_adapter.py
tests/unit/runtime_lab/test_sop_adapter_contract.py
tests/integration/runtime_lab/test_runtime_lab_sop_adapter_contract.py
```

Use the existing mock adapter only as a guide. 031 should make the contract
explicit enough for 032 to implement a real Chatflow adapter without changing
the runtime service.

## Contract Tests

Required tests:

- start returns waiting result with checkpoint;
- continue returns updated collected variables;
- completed result marks task completed through runtime service;
- suspend returns serializable checkpoint;
- resume restores checkpoint;
- adapter failure is normalized;
- adapter cannot mutate runtime task ledger directly.

## Dependency Check

Use a lightweight import scan or architecture test to assert that existing
Workflow/Chatflow modules do not import `runtime_lab`.

## Evidence

Use:

```text
artifacts/slices/031-chatflow-sop-adapter-contract/
  031.0/
  031.1/
  ...
```

No frontend or browser UAT is required.

## Non-Goals

Do not:

- wire real Chatflow execution;
- change Chatflow public API;
- add new frontend routes;
- implement FAQ/RAG/Agent/handoff.
