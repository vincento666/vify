# Plan 040: Runtime Fallback E2E And Lab Acceptance

## Architecture

040 validates the full stack:

```text
runtime-lab API
  -> handoff hard stops
  -> FAQ exact
  -> FAQ semantic
  -> SOP/resume arbitration
  -> RAG
  -> controlled Agent
  -> handoff escalation
  -> frontend runtime-lab inspector
```

## TDD Strategy

RED first:

- create backend E2E scenario matrix tests before any missing UI/backend
  hardening;
- create frontend route-inspector tests only if fallback evidence cannot be
  observed in the existing 034 lab;
- create browser UAT script for representative mixed flows.

GREEN:

- only fix gaps found by the acceptance tests;
- do not add new algorithms unless previous specs missed a required behavior.

## Browser UAT

Use the 034 lab page and extend it only if needed to display:

- route action;
- source layer;
- policy decision;
- FAQ/RAG/Agent evidence;
- task ledger;
- handoff status/context.

Representative browser conversations:

- active refund SOP + baggage FAQ answer + continue refund;
- active change SOP + explicit handoff;
- no-active semantic FAQ;
- no-active RAG long-tail answer;
- unresolved request -> Agent clarification -> repeated failure -> handoff.

## Evidence

Use:

```text
artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/
  040.1/
  040.2/
  040.3/
```

## SDD Gate

040 may start only after 033 and 036-039 are implemented and their slice
evidence exists. It is an acceptance and hardening spec, not a place to add new
fallback algorithms.

Each acceptance slice must update `spec.md`, `plan.md`, `tasks.md`, and the
corresponding artifact directory. 040 is complete only when the full scenario
matrix has expected-vs-actual evidence, active/suspended task preservation is
audited, and any frontend evidence changes pass the required rem/frontend gates.

## Non-Goals

- no production analytics dashboard;
- no human console;
- no mandatory live LLM credentials.
