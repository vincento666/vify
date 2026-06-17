# Feature Spec: Customer Assistant Destub Demo Workers

## Status

Complete.

## User Story

As an operator running the MVP customer-assistant demo, I see seeded and default
worker routes described as productized chatflow/workflow/react workers instead
of leftover `stub_qa` placeholders, while the demo remains deterministic and
safe to run without live providers.

## Functional Requirements

- One-click MVP demo seed must not create customer-assistant demo tasks with
  `worker_type = "stub_qa"`.
- Default customer-assistant worker profiles must not expose
  `baggage_allowance_stub`, `fake_stub_qa_model`, or a `stub_qa` worker route
  in MVP operator flows.
- Deterministic demo worker behavior must remain available through configured
  productized worker names consistent with the worker-profile model.
- Any legacy `stub_qa` compatibility paths outside seeded/default MVP flows
  must remain isolated and unchanged unless a focused test proves they block
  this slice.

## Non-Goals

- Frontend changes.
- Changing normal customer-assistant proposed-action generation; slice 126 owns
  that service path.
- Removing all legacy `stub_qa` compatibility from async runtime, router, or
  historical tests.
- Real provider calls, real RAG, or external tool execution.

## Acceptance Criteria

- RED evidence shows seeded/default MVP worker surfaces still expose `stub_qa`
  or stub-named profile refs before implementation.
- Focused unit/integration gates prove seeded customer-assistant demo tasks and
  default worker-profile JSON contain no productized-demo `stub_qa` markers.
- Focused worker behavior tests prove deterministic demo output is still
  produced through the productized worker route.
- Browser UAT is not required for 127.1 because this slice changes backend seed
  data and default configuration only; no frontend files or browser workflows
  are modified. Persisted topology tests cover the user-visible seeded state.
- Docs/tasks record evidence paths and final status.

## Evidence

Evidence lives under
`artifacts/slices/127-customer-assistant-destub-demo-workers/127.1/`.

- RED: `red.txt`
- Focused unit: `unit.txt`
- Focused integration: `integration.txt`
- Worker-profile API integration: `worker_profiles_integration.txt`
- MVP bootstrap contract: `bootstrap_contract.txt`
- Ruff: `ruff.txt`
- Browser UAT: not required; backend seed/default configuration only.
