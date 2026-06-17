# Feature Spec: Customer Assistant Sub-Agent Workbench Controls

## Status

Complete.

## User Story

As a customer-service operator in the seeded MVP workbench, I can launch a customer-assistant sub-agent for the current session, watch that run progress through the existing event/audit surfaces, and keep the workbench synchronized after the run completes.

## Functional Requirements

- The frontend API client must expose the existing harness `spawn_sub_agent` endpoint and run-detail endpoint.
- The runtime state layer must provide a single operation that:
  - requires an active customer-assistant session;
  - sends an operator-scoped sub-agent request with a deterministic message;
  - refreshes tasks, events, proposed actions, metrics, and operator audit after the spawn/run path returns;
  - records lightweight sub-agent status for the workbench.
- The operator workbench must expose a compact sub-agent control outside the customer lane.
- The control must be disabled until a session exists and must show running/completed/failed status.
- The customer lane must not expose sub-agent internals.

## Non-Goals

- New backend harness semantics; spec 116 already covers tenant-safe backend execution.
- Generic multi-agent orchestration UI.
- Real external channel delivery.
- Replacing existing event/audit timeline panels.

## Acceptance Criteria

- RED frontend tests fail before API/runtime/panel support exists.
- API test proves the client calls `/v1/customer-assistant/harness/spawn-sub-agent` and `/v1/customer-assistant/runs/{runId}` with the expected payload.
- Runtime test proves sub-agent spawn refreshes all ledgers and preserves completed sub-agent status.
- Panel contract proves the control renders in the operator progress area, not the customer lane.
- Focused frontend unit/rem gate passes.
- Browser UAT verifies a seeded story can launch a sub-agent and display resulting evidence.

## Evidence

Evidence lives under `artifacts/slices/117-customer-assistant-sub-agent-workbench-controls/117.1/`.

- RED: `red.txt`
- First green: `frontend-first-green.txt`
- Focused frontend/rem: `frontend-rem.txt`
- Full frontend unit: `frontend-full.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `uat.txt`, `uat-report.json`, `uat.md`
- Screenshot: `screenshots/sub-agent-workbench-control.png`
