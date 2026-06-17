# 140 Customer Assistant Configurable ReAct Worker

## Status

Complete.

## Goal

Make customer-assistant worker profiles drive the ReAct worker runtime, not only
the operator-facing metadata. A configured `react_worker` profile must control
the worker ref, model/prompt/tool/risk refs shown in evidence and the actual
tool allowlist used by the restricted worker.

## Acceptance Criteria

- A worker profile override can route `refund_ticket` to `react_worker`.
- The profile `toolRefs` becomes the ReAct worker allowed-tool list.
- If a profile removes `lookup_order`, the default ReAct model's attempted
  `lookup_order` call is rejected with `TOOL_NOT_ALLOWED`, no write action is
  proposed, and debug events record `react_tool_call_failed`.
- Existing default `refund_status_react` behavior remains available.
- MySQL8-backed integration gates pass.
- Browser UAT opens the real customer-assistant workbench and verifies a
  configured ReAct worker profile writes `workerConfigRefs` into task evidence.

## Non-Goals

- Building a full worker-skill admin resource model.
- Adding new external tools or real tool execution.
- Changing proposed-action confirmation semantics.

## Evidence

Evidence lives under
`artifacts/slices/140-customer-assistant-configurable-react-worker/140.1/`.

- RED tool policy: `red.txt`
- RED config refs: `config-refs-red.txt`
- Focused green: `focused-green.txt`
- Config refs green: `config-refs-green.txt`
- Unit/integration green: `unit-integration-green.txt`
- Contract smoke: `contract-smoke.txt`
- Customer-assistant regression: `customer-assistant-regression.txt`
- Browser UAT: `browser-uat.txt`
- Browser screenshot: `screenshots/react-worker-profile-config.png`
- Ruff: `ruff-2.txt`
