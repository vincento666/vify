# Spec 054: Customer Assistant Synthetic Eval And LLM Promotion Readiness

## Goal

Build a synthetic evaluation corpus and promotion gate for the customer
assistant, so the project does not wait for production traffic before making
LLM primary-path decisions.

This spec turns the demo/project context into an explicit data strategy:
generate representative cases, run deterministic and LLM-shadow candidates
against them, and use the results as the readiness gate for Spec 055.

## Dependency

054 depends on:

- 047 actor and LLM shadow events;
- 048 L1 runtime event stream;
- 049 restricted ReAct worker events;
- 050 proposed action lifecycle;
- 051 eval data foundation;
- 052 eventful sub-agent contract.

## Product Boundary

In scope:

- synthetic customer-assistant scenario matrix;
- generated eval cases for customer, operator, and system turns;
- refund, baggage QA, mixed/multi-task, ambiguous, missing-field, cancellation,
  and high-risk action cases;
- deterministic oracle fields for task recognition, recommendation, safety, and
  event expectations;
- fake-mode default gate with zero live LLM calls;
- optional live LLM batch gate using existing provider config;
- Browser UAT script that replays the highest-value scenarios through the
  operator panel;
- database-backed Chatflow/SOP readiness checks for the target MySQL 8
  migration path.

Out of scope:

- claiming production statistical accuracy;
- long-running online eval loops;
- LLM-as-judge as a default gate;
- replacing the deterministic runtime;
- real external writes.
- creating the full MySQL 8 migration.

## Chatflow Data Readiness

Customer-assistant refund/chatflow behavior must not depend on accidental local
IDs in a developer `.env`.

054 must define and test a readiness strategy for Chatflow/SOP data:

```text
required_sop_key -> database chatflow/workflow row -> runtime binding
```

During the MySQL 8 migration, the MVP may use one of these strategies:

- seed required Chatflow/SOP definitions into the target database;
- export/import known-good Chatflow fixtures;
- run with explicit fallback mock bindings and record that production Chatflow
  data is not ready.

Browser UAT must record which strategy was used. A missing Chatflow row should
be reported as data-readiness failure, not mistaken for a runtime failure.

## Dataset Size

MVP dataset target:

```text
20 to 40 synthetic cases
```

Required coverage:

- straightforward refund request;
- refund request missing ticket/order number;
- refund continuation with order number;
- refund cancellation;
- baggage allowance QA;
- combined refund and baggage request;
- ambiguous customer message;
- operator internal question;
- system-triggered follow-up;
- high-risk refund submission proposed but not executed;
- unsafe direct-write attempt;
- worker timeout/failure fixture;
- harness spawn-sub-agent scenario.

## Promotion Metrics

054 does not require the LLM to pass as primary path. It only produces the
readiness report.

Minimum report fields:

```text
totalCases
taskRecognitionPassRate
recommendationPassRate
safetyPassRate
schemaFailureRate
fallbackRate
eventCoveragePassRate
liveModelCalls
```

For default gates, `liveModelCalls` must be `0`.

## Shadow Mode Boundary

Shadow mode is evidence-only. LLM-shadow candidates may be generated, parsed,
scored, diffed, exported, and included in the promotion report, but they must
not:

- mutate the task ledger;
- dispatch or cancel workers;
- create or execute proposed actions;
- replace deterministic recommendations or customer drafts;
- change the response returned by the runtime.

Any shadow output that would have changed behavior must be recorded as
evaluation evidence or diff metadata only.

## Acceptance Criteria

- Synthetic cases are committed as fixtures or generated deterministically.
- Eval runner can compare deterministic baseline and LLM-shadow candidate
  outputs against expected case metadata.
- LLM-shadow candidates are proven to be evidence-only and cannot mutate runtime
  behavior.
- Safety checks prove high-risk writes stay proposed until operator confirms.
- Chatflow/SOP data readiness is checked against the active database strategy.
- Browser UAT covers at least five representative cases through the operator
  panel.
- 054 produces a clear go/no-go recommendation for starting Spec 055.

## MVP Exit

054 is complete when it can answer this question with evidence:

```text
Can this demo project safely start LLM primary-path work without production data?
```

The answer may be `go`, `go with explicit mocked Chatflow data`, or `no-go`.
054 must not implement the LLM primary path itself.
