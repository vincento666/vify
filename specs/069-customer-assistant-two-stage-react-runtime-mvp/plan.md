# Plan 069: Customer Assistant Two-Stage ReAct Runtime MVP

## Smooth Upgrade Strategy

Rollout stages:

```text
shadow_two_stage
  -> diff against controlled loop
fake_primary_with_fallback
  -> selected only in tests/UAT
opt_in_primary
  -> feature flag
```

Do not replace the controlled loop by default.
Shadow mode must not dispatch extra workers, call side-effecting tools, or
mutate task/runtime state.

## Runtime Shape

```text
Stage 1: think/plan/task recognition/safety
Stage 2: execute allowed task commands or worker actions
Final: recommendation aggregation
```

If Stage 2 has no action, final recommendation is returned.
Stage 2 is limited to allowlisted commands/workers. Raw internal reasoning is
not persisted or displayed.

## Progression Telemetry

Two-Stage modes record debug-only structured progression events:

```text
plan        -> legacy task_recognition
action      -> legacy task_execute_parallel
observation -> legacy task_execute_parallel
final       -> legacy generate_recommendation
```

The payloads contain compact command, worker-dispatch, worker-result, and task
status summaries only. They must not contain raw chain-of-thought or hidden
reasoning fields, and they do not replace existing `task_recognized`,
worker/recommendation, or API response fields.

## Finalize Contract

The Two-Stage final step is the compatible replacement for the existing
`generate_recommendation` phase, not a free-form chat answer.

Input pack:

```text
task ledger
worker results
pending/waiting worker evidence
Chatflow blocking-node prompt/followup/pendingPrompt
proposed actions
safety state
conversation context
debug/evidence refs
```

Output schema:

```text
operatorRecommendation
customerReplyDraft
proposedActions
taskSummaries
warnings
evidenceRefs
```

Prompt guardrails:

- produce the same product fields as `generate_recommendation`;
- use evidence only, do not invent facts;
- preserve concrete waiting prompts/questions from workers and Chatflow nodes in
  `customerReplyDraft`;
- explain waiting reason and next operator action in `operatorRecommendation`;
- summarize proposed actions but never execute them;
- return strict JSON matching the existing recommendation schema;
- no raw chain-of-thought.

Fallback to the controlled `generate_recommendation` path when final output
fails schema, safety, evidence, or prompt-preservation validation.

## Equivalence Checks

Before opt-in:

- compare TaskCommand list;
- compare ledger mutation;
- compare worker dispatch;
- compare recommendation/draft shape;
- compare proposed actions.
- compare waiting reason, checkpoint refs, evidence refs, and preserved
  blocking-node prompt text.

Promotion from shadow to opt-in primary requires a documented threshold over the
054 synthetic/golden suite.
