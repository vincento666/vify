# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Latest completed slice:

```text
222.14.3 Backend Autonomous Worker MVP (complete)
```

Next implementation slice:

```text
222.14.4 Live Gate Rerun
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
branch: codex/spec-222-14-3-autonomous-worker
path: /Users/vincento/work/develop/hify
base: 38ac37f3 codex/spec-222-14-2-aggregate-eval
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because this is one active Builder stream and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
app/modules/ai_assistant/web/router.py
tests/contract/test_ai_assistant_session_runtime_api.py
specs/222-ai-assistant-general-harness-mvp/
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14.3/
```

Behavior target:

```text
messages/async queues a durable run and the backend module autonomously
consumes it in-process. Explicit worker/process remains idempotent and SSE
streaming remains subscribe/replay only.
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
fix requires broker, standalone worker service, schema migration, or new dependency
scope expands outside AI Assistant async worker trigger and its tests
events/stream needs to start execution
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened tests, or secret exposure
slice completes but cannot be committed safely
```
