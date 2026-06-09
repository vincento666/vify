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

Use the 034 lab page or live runtime-lab API docs and extend UI only if needed
to display:

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

Actual 2026-06-09 UAT used the live FastAPI docs page plus controlled API
requests against `http://127.0.0.1:18088/api/v1/runtime-lab`. No frontend/rem
changes were needed. Browser policy blocked `data:` and `file:` report pages,
so the full transcript is stored as JSON/HTML artifacts and the live docs page
is captured as the browser screenshot.

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

Completion note 2026-06-09: acceptance exposed two runtime hardening gaps, both
within existing MVP policy scope:

- low-confidence RAG retrieval now defers to controlled Agent fallback when an
  Agent is configured;
- default Fake Agent can recommend handoff for complex/ambiguous dispute cases,
  with PolicyGate retaining final authority.

## Non-Goals

- no production analytics dashboard;
- no human console;
- no mandatory live LLM credentials.

## Unified Arbitration Refactor Gate

After the 2026-06-09 routing revision, 040 must prove the final architecture:

```text
hard stop
  -> unified hybrid candidate recall
  -> central constrained LLM arbitration
  -> PolicyGate
  -> typed executor
```

The acceptance matrix must include FAQ/SOP, semantic FAQ/SOP, and RAG/SOP
conflict cases and must prove non-hard-stop decisions contain a visible central
arbitration step.
