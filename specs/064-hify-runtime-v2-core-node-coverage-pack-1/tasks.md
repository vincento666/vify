# Tasks 064: Hify Runtime V2 Core Node Coverage Pack 1

## 064.0 Sign-off

- [x] Confirm 064 extends shared runtime core node coverage.
- [x] Confirm LLM/tool/API/agent/nested/code nodes are out of scope.
- [x] Confirm unsupported nodes still block whole-graph v2 execution.
- [x] Confirm `INFORMATION_COLLECTION` support is deterministic only.

## 064.1 Node Compatibility Fixtures

- [x] RED: core node output parity tests fail for missing v2 executors.
- [x] Add fixtures comparing legacy and v2 outputs.
- [x] Add route decision and variable scope assertions.
- [x] Add checkpoint and failure-behavior parity assertions.
- [x] Add unsupported fixture for LLM-dependent information collection.

## 064.2 Supported Node Executors

- [x] Add v2 support for `HUMAN_INPUT`.
- [x] Add v2 support for `TEXT_PROCESS`.
- [x] Add v2 support for `JSON_PARSE`.
- [x] Add v2 support for `VARIABLE_ASSIGN`.
- [x] Add v2 support for `VARIABLE_AGGREGATION`.
- [x] Add v2 support for `CONDITION`.
- [x] Add v2 support for `INTENT_RECOGNITION`.
- [x] Add v2 support for deterministic/schema-driven
      `INFORMATION_COLLECTION` only.

## 064.3 Event Coverage

- [x] Emit L1 node events for each supported node.
- [x] Emit node status transitions needed by canvas/debug consumers:
      `RUNNING`, `WAITING`, `COMPLETED`, `FAILED`, and `SKIPPED` where
      applicable.
- [x] Preserve blocking-node display text in events/checkpoints:
      `QUESTION.question`, `HUMAN_INPUT.prompt`, and
      `INFORMATION_COLLECTION.followup`.
- [x] Emit L2 route/variable/checkpoint events where applicable.
- [x] Prove failed supported node emits failure state and stops downstream
      execution unless an explicit supported error/fallback path exists.

## 064.4 Compatibility Checker

- [x] Update supported node set.
- [x] Prove unsupported LLM/tool/agent/code/nested nodes block v2.
- [x] Prove LLM-dependent `INFORMATION_COLLECTION` blocks v2.

## 064.5 Gates

- [x] Run workflow/chatflow focused integration tests.
- [x] Run Chatflow v2 Browser UAT for one expanded graph.

Evidence:

- RED: `artifacts/slices/064-hify-runtime-v2-core-node-coverage-pack-1/red.txt`
- Integration: `artifacts/slices/064-hify-runtime-v2-core-node-coverage-pack-1/integration-expanded.txt`
- Backend gates: `artifacts/slices/064-hify-runtime-v2-core-node-coverage-pack-1/backend-gates.txt`
- Browser UAT: `artifacts/slices/064-hify-runtime-v2-core-node-coverage-pack-1/uat.md`
