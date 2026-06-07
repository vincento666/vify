# 032.2 RED Test Plan

## Status

Pre-implementation sign-off only. No tests have been written in this gate.

032.2 is not complete until failing RED tests are added and their output is
saved.

## Required RED Coverage

The RED tests must fail before implementation for:

- `ChatflowSopRuntimeAdapter.start_sop` starting the real Chatflow fixture;
- `continue_sop` resuming a waiting information-collection checkpoint;
- `suspend_sop` mapping an existing waiting checkpoint into `SopCheckpoint`;
- `resume_sop` restoring from persisted checkpoint;
- completing the fixture after confirmation;
- normalized failure when no waiting checkpoint exists for suspend/resume.

## Fixture Requirement

Add one test-only Chatflow fixture if no existing helper is suitable:

```text
START -> INFORMATION_COLLECTION(order_no) -> QUESTION(confirm) -> END
```

The fixture must stay in tests and must not become production seed data.

## Non-Goals

Do not:

- implement `ChatflowSopRuntimeAdapter` in 032.2;
- change runtime route arbitration;
- change Chatflow public API;
- add frontend or browser UAT.
