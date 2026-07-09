# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Latest completed slice:

```text
222.14.5 Durable Idempotency And Circuit Breaker Spec (complete)
```

Next implementation slice:

```text
Spec 222 corrective wave complete
```

This file is the spec-facing loop pointer. Other loop engineering files such as
`loop/STATE.md` and `loop/VERIFIERS.md` are operational sprint artifacts; they
must not become alternate spec sources of truth.

## Active Spec

Spec id:

```text
222-ai-assistant-general-harness-mvp
```

Spec files:

```text
specs/222-ai-assistant-general-harness-mvp/spec.md
specs/222-ai-assistant-general-harness-mvp/plan.md
specs/222-ai-assistant-general-harness-mvp/tasks.md
```

## Worktree

```text
branch: codex/spec-222-14-5-idempotency-spec
path: /Users/vincento/work/develop/hify
base: 23665afd codex/spec-222-14-4-live-gate
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because this is one active Builder stream and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
specs/224-ai-assistant-durable-toolrunner-idempotency/
specs/README.md
specs/222-ai-assistant-general-harness-mvp/
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14.5/
```

Behavior target:

```text
Spec 224 defines durable ToolRunner idempotency and circuit breaker semantics,
including operation key generation, UNKNOWN lifecycle, release authority,
fallback identity, read-vs-side-effect rules, and persistent breaker state.
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
implementation code is needed in this docs-only slice
scope expands into sandbox, HA, multi-tenant infra, or real business adapters
the spec fails to answer required key/UNKNOWN/fallback/breaker questions
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened tests, or secret exposure
slice completes but cannot be committed safely
```
