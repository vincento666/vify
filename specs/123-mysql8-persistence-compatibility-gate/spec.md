# Spec 123: MySQL8 Persistence Compatibility Gate

## Goal

Productize the MVP demo MySQL8 persistence concern into a repeatable gate for
the customer-assistant and Chatflow/Workflow runtime surfaces. The default gate
must run locally without Docker or a live MySQL server, while preserving an
opt-in live MySQL8 round-trip when credentials are supplied.

## Scope

- Runtime v2 metadata:
  - `workflow_run` input/output/error/timing metadata.
  - `workflow_node_run` inputs/outputs/timing metadata.
  - `chatflow_session` variables/current run metadata.
  - `chatflow_event` payload sequence metadata.
  - `chatflow_checkpoint` execution context, outputs, scopes, and resume schema.
- Chatflow/Workflow snapshots:
  - `workflow` Chatflow/Workflow records.
  - `workflow_published_version` snapshot and validation JSON.
  - `chatflow_channel_config` channel configuration JSON.
- Runtime Lab continuity:
  - `runtime_lab_session`, task, checkpoint, event, and command JSON/text
    payloads used by the demo runtime path.
- Customer assistant ledgers:
  - session context, run input/response/warnings, task checkpoints/snapshots,
    events, worker runs/events, proposed actions, and worker profile tool refs.

## Requirements

- FR-001: A deterministic pytest target validates the MVP persistence table set
  compiles under the SQLAlchemy MySQL dialect.
- FR-002: The local gate verifies SQLAlchemy `JSON`, `DateTime`, `Text`, Boolean,
  and index/unique metadata used by the MVP persisted surfaces.
- FR-003: The local gate round-trips representative JSON/text/datetime payloads
  through repository/table contracts without requiring Docker.
- FR-004: A live MySQL8 test remains opt-in via
  `HIFY_MYSQL8_TEST_DATABASE_URL`; without credentials it must skip explicitly
  with a useful message.
- FR-005: Evidence must be saved under
  `artifacts/slices/123-mysql8-persistence-compatibility-gate/123.1/`.

## Non-Goals

- No frontend UI changes.
- No workflow runtime semantic changes.
- No production data migration or Docker provisioning.
- No MySQL-native vector/RAG implementation.

## Acceptance

- RED evidence shows the gate initially failed because the MVP coverage manifest
  or evidence was missing.
- Focused MySQL8 compatibility pytest target passes locally.
- Ruff passes for changed Python files.
- Live MySQL8 result is recorded as either executed or explicitly skipped.
