# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Latest completed slice:

```text
222.14.2 Aggregate Eval Runtime Evidence (complete)
```

Next implementation slice:

```text
222.14.3 Backend Autonomous Worker MVP
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
branch: codex/spec-222-14-2-aggregate-eval
path: /Users/vincento/work/develop/hify
base: bedcb368 codex/spec-222-14-1-event-sequence
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because this is one active Builder stream and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
app/modules/ai_assistant/domain/aggregate_production_eval.py
tests/eval/test_ai_assistant_aggregate_production_eval.py
specs/222-ai-assistant-general-harness-mvp/
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14.2/
```

Behavior target:

```text
Aggregate production eval proves runtime behavior from evidence artifacts,
not from source/test-string matches, for token streaming, reconnect recovery,
tool self-correction, file workspace safety, and context visibility.
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
fix requires company-wide eval framework changes, new dependency, or schema work
scope expands outside AI Assistant aggregate eval and its tests
runtime evidence contract must change beyond current Spec 222.14.2 boundary
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened tests, or secret exposure
slice completes but cannot be committed safely
```
