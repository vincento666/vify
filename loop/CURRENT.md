# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Latest completed slice:

```text
222.14.4 Live Gate Rerun (complete)
```

Next implementation slice:

```text
222.14.5 Durable Idempotency And Circuit Breaker Spec
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
branch: codex/spec-222-14-4-live-gate
path: /Users/vincento/work/develop/hify
base: 0b915aea codex/spec-222-14-3-autonomous-worker
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because this is one active Builder stream and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
tests/e2e/test_ai_assistant_live_qwen36_real_case_uat.py
specs/222-ai-assistant-general-harness-mvp/
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14.4/
```

Behavior target:

```text
Current code reruns the existing 222.11 OpenRouter live gate against
qwen/qwen3.6-27b, proving raw streaming, mock aviation adapter seam cases,
approval, audit redaction, context, token, and cost budget evidence.
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
live provider key, network, quota, or model availability fails
scope expands to new provider, new model, real airline systems, or code changes
artifacts contain an API key or unredacted secret
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened tests, or secret exposure
slice completes but cannot be committed safely
```
