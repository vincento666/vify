# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Latest completed slice:

```text
222.13 Tool Observation Self-Correction Correction (complete)
```

Pending after this slice:

```text
222.14 Production Hardening Backlog (proposed-confirmation)
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
branch: codex/spec-222-13-tool-self-correction
path: /Users/vincento/work/develop/hify
base: a57cb783 codex/runtime-v2-production-upgrade
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because this is one active Builder stream and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
app/modules/ai_assistant/
frontend/src/views/aiAssistant/
frontend/src/api/aiAssistant*
tests/unit/ai_assistant/
tests/contract/test_ai_assistant_*.py
tests/e2e/test_ai_assistant_*.py
specs/222-ai-assistant-general-harness-mvp/
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.13/
```

Behavior target:

```text
Recoverable tool timeout, 5xx, and rate-limit observations must feed a
repair/replan loop. The run may retry with repaired arguments, select a fallback
adapter/tool, or degrade within budget. Permission, sandbox, approval, and
exhausted-budget failures remain structured terminal failures.
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
scope needs new dependency, schema/API migration, production secret, push,
release, real external service, or irreversible action
222.13 acceptance requires changing 222.14 backlog boundary
same verifier failure repeats twice without narrower hypothesis
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened tests, or missing evidence
merge target becomes ambiguous or dirty
slice completes but cannot be committed safely
```
