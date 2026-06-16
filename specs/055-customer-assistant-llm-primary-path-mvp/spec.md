# Spec 055: Customer Assistant LLM Primary Path MVP

## Goal

Promote the customer-assistant LLM path from shadow-only to an opt-in primary
path for task recognition and recommendation, while preserving deterministic
fallback and safety controls.

055 exists because the project is a demo/product integration rather than a
long-running production-learning loop. It should be basically usable when
merged into the host project.

## Dependency

055 depends on:

- 047 LLM shadow client and strict parsers;
- 050 proposed action lifecycle;
- 054 synthetic eval readiness report;
- 054 Chatflow/SOP data readiness result.

## Product Boundary

In scope:

- feature-flagged LLM primary mode;
- task-recognition LLM candidate can produce structured task commands;
- recommendation LLM candidate can produce operator recommendation and customer
  draft;
- recommendation LLM candidate establishes the strict schema/prompt guardrails
  that later Two-Stage ReAct finalization must reuse or remain compatible with;
- deterministic fallback on schema failure, provider failure, low confidence,
  unsupported commands, or safety violation;
- all high-risk writes remain proposed actions;
- event evidence records primary/fallback decision.
- primary path can use database-backed Chatflow/SOP readiness information when
  deciding whether to dispatch a worker or fall back.

Out of scope:

- autonomous direct execution of high-risk actions;
- generic prompt-building UI;
- memory beyond the existing customer-assistant session/task ledger;
- production A/B testing infrastructure.
- solving database migration or seed-data gaps discovered by 054.

## Runtime Modes

```text
deterministic
shadow
llm_primary_with_fallback
```

Default must remain deterministic unless explicitly configured.

## Shadow Mode Boundary

`shadow` mode is not a soft primary path. It runs deterministic behavior as the
only selected runtime path, then records LLM candidates for comparison.

In `shadow` mode, LLM output must not:

- mutate the task ledger;
- dispatch, resume, suspend, or cancel workers;
- create proposed actions;
- select the operator recommendation or customer draft;
- alter the returned runtime response.

Only `llm_primary_with_fallback` may select LLM output, and only after schema,
confidence, safety, and Chatflow/SOP readiness checks pass.

## Recommendation Prompt Boundary

LLM recommendation output is a constrained replacement for the deterministic
recommendation aggregator, not a free-form answer.

The recommendation prompt/schema must preserve:

- `operatorRecommendation`;
- `customerReplyDraft`;
- proposed action summaries without execution;
- waiting reason and checkpoint refs when a task is waiting;
- exact worker/Chatflow blocking prompt text when it is the source of the
  customer draft.

Spec 069 Two-Stage ReAct finalization must reuse this schema or prove field-level
compatibility with it.

## Fallback Rules

Fallback to deterministic if:

- LLM call fails;
- response is not strict JSON;
- schema validation fails;
- command type is unsupported;
- required worker binding is missing;
- bound Chatflow/SOP data is missing in the active database;
- confidence is below configured threshold;
- safety validator rejects the candidate;
- proposed action would bypass confirmation.

## Acceptance Criteria

- LLM primary mode is opt-in and off by default.
- Shadow mode remains evidence-only and never changes runtime behavior.
- Synthetic eval gate from 054 passes configured thresholds.
- Chatflow/SOP data readiness is either green or explicitly mocked for demo
  mode.
- Fallback events explain why deterministic path was used.
- Browser UAT demonstrates at least one LLM-primary successful case and one
  fallback case.
- High-risk writes still require operator confirmation.

## MVP Exit

055 is complete when fake-gated LLM primary mode can control task recognition
and recommendation for selected synthetic cases, while every unsafe or invalid
case falls back with an explainable event.

Live provider UAT is desirable but remains opt-in unless model credentials and
provider config are available in the environment.
