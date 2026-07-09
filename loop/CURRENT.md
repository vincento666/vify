# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Latest completed slice:

```text
222.14.1 Event Sequence Concurrency Safety (complete)
```

Next implementation slice:

```text
222.14.2 Aggregate Eval Runtime Evidence
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
branch: codex/spec-222-14-1-event-sequence
path: /Users/vincento/work/develop/hify
base: 699cc6d4 codex/spec-222-14-corrective-contract
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because this is one active Builder stream and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
app/modules/ai_assistant/infra/repository.py
tests/integration/ai_assistant/test_harness_repository.py
tests/contract/test_ai_assistant_event_sequence_api.py
tests/contract/test_ai_assistant_streaming_api.py
tests/contract/test_ai_assistant_session_runtime_api.py
tests/e2e/test_ai_assistant_session_runtime_e2e.py
tests/e2e/test_ai_assistant_streaming_e2e.py
specs/222-ai-assistant-general-harness-mvp/
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14.1/
```

Behavior target:

```text
AI Assistant events within the same run replay as strict 1..N sequence under
concurrent append. API afterSequence replay and snapshot/SSE resume remain
ordered and trustworthy.
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
fix requires schema migration, new unique index, broker, or dependency
scope expands outside app/modules/ai_assistant event append/replay
runtime v2, customer assistant, or chatflow event systems must change
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened tests, or secret exposure
slice completes but cannot be committed safely
```
