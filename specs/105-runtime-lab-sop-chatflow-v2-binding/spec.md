# Feature Spec: Runtime Lab SOP Chatflow V2 Binding & Resume Lifecycle

## Status

Complete.

## User Story

As a demo operator using the Runtime Lab airline SOP demo, I can rely on the default SOP-to-Chatflow binding path to use runtime v2 async runs, while the old multi-intent suspend/resume router still behaves the same across repeated wait/resume turns.

## Functional Requirements

- When `runtime_lab_sop_chatflow_ids` is configured, the default Runtime Lab service factory must wire `ChatflowSopRuntimeAdapter` with a `ChatflowRuntimeV2Service`.
- The v2 service must use the same SQLAlchemy session as the Runtime Lab service factory so run events, checkpoints, and node state are persisted in the same request/database boundary.
- Resuming a runtime v2 Chatflow run from Runtime Lab may legally interrupt again on a later node; the service must preserve the new waiting checkpoint and keep the SOP task running instead of returning a generic failure.
- Legacy fallback behavior remains unchanged for unbound SOPs and unsupported v2 graphs.
- Existing Runtime Lab multi-intent suspend/resume behavior must remain green.

## Non-Goals

- Changing SOP classification or recall policy.
- Replacing the fallback fake SOP adapter.
- Changing live LLM/provider selection.
- Adding new UI controls.

## Acceptance Criteria

- RED factory contract proves the default Runtime Lab Chatflow binding lacks a runtime v2 service before implementation.
- RED API E2E proves Runtime Lab v2 resume used to fail when the resumed Chatflow interrupted again.
- Focused unit tests prove the default factory wires a `ChatflowRuntimeV2Service`.
- Existing Runtime Lab Chatflow SOP adapter integration tests remain green.
- Existing Runtime Lab Chatflow SOP API E2E remains green.
- Browser UAT verifies the default configured Runtime Lab service can run a multi-intent suspend/resume flow through runtime v2 and emit `workflow_run_started`, `workflow_node_waiting`, and `workflow_run_resumed` trace events.

## Evidence

Evidence lives under `artifacts/slices/105-runtime-lab-sop-chatflow-v2-binding/105.1/`.

- RED: `red.txt`
- Unit: `unit.txt`
- Integration: `integration.txt`
- API E2E focused RED/GREEN: `api-e2e-focused.txt`
- API E2E: `api-e2e.txt`
- Runtime v2 regressions: `runtime-v2-regressions.txt`
- Runtime Lab service regression: `service-regression.txt`
- Ruff: `ruff.txt`
- Browser UAT: `browser-uat.txt`
- Browser UAT report: `browser-uat.md`
- Screenshot: `screenshots/runtime-lab-sop-v2-binding.png`
