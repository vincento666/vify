# Spec 051: Customer Assistant Eval Data Foundation

## Goal

Build the first evaluation data path for the customer-assistant runtime. 051
does not require a large curated dataset. It creates the schemas, export path,
and initial golden cases needed to evaluate later LLM promotion decisions.

## Dependency

051 depends on evidence and events from:

- 047 LLM shadow events;
- 048 runtime timing events;
- 049 worker safety events when available;
- 050 action feedback when available.

## Eval Coverage

Primary:

- task recognition correctness;
- recommendation usefulness and safety;
- worker/action safety.

Secondary smoke:

- end-to-end business outcome.

## Data Sources

```text
customer_assistant_event debug payloads
shadow baseline/shadow/diff events
operator confirm/reject/adoption signals
proposed-action execution outcomes
handwritten golden cases
```

051 should make export possible even if production-like volume is not available
yet.

## MVP Scope Guard

051 is a data-path MVP. It creates schemas, exporters, handwritten golden
cases, and deterministic reports. It does not require a large production
dataset, LLM-as-judge, live model calls, or automatic model promotion.

## Metrics

Initial deterministic metrics:

- task type match;
- task key/business key match;
- unsafe proposed action leakage;
- recommendation non-empty;
- customer draft non-empty;
- run elapsedMs;
- worker elapsedMs;
- timeout/failure count.

LLM-as-judge can be explored later, but 051 should not depend on it.

## Acceptance Criteria

- Eval case schema exists.
- Runtime/shadow events can be exported into candidate eval cases.
- Handwritten golden cases run in CI.
- Report includes task recognition, recommendation, and safety sections.
- No live LLM calls are required for default eval gates.
