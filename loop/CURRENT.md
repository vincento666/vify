# Current Loop Scope: Spec 222 AI Assistant Harness

## Status

Active contract sprint:

```text
222.14 Corrective Wave Contract (contract construction)
```

Next implementation slice after this contract:

```text
222.14.1 Event Sequence Concurrency Safety
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
branch: codex/spec-222-14-corrective-contract
path: /Users/vincento/work/develop/hify
base: 4a987d67 codex/runtime-v2-production-upgrade
merge target: codex/runtime-v2-production-upgrade
```

Current worktree is used because the work is a docs-only contract slice and no
unrelated dirty changes were present before the branch was created.

## Frozen Scope

Allowed:

```text
specs/222-ai-assistant-general-harness-mvp/spec.md
specs/222-ai-assistant-general-harness-mvp/plan.md
specs/222-ai-assistant-general-harness-mvp/tasks.md
loop/CURRENT.md
loop/STATE.md
loop/VERIFIERS.md
artifacts/slices/222-ai-assistant-general-harness-mvp/222.14-contract/
```

Behavior target:

```text
Turn the old 222.14 backlog into a bounded corrective wave contract:
event sequence concurrency safety, runtime-evidence aggregate eval, same-process
backend autonomous worker MVP, env-gated 222.11 live rerun, and a separate
durable idempotency/circuit breaker spec task.
```

Explicit non-goals:

```text
real OS/container sandbox isolation
network/CPU/memory isolation
multi-tenant infrastructure
cross-machine HA worker takeover
standalone worker service
business adapter expansion
large UI redesign
production push/release
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
contract requires implementation before spec confirmation
scope expands into sandbox, HA worker, multi-tenant, production, or business adapter work
acceptance cannot be made objectively checkable
Checker finds missing evidence or gate bypass
Reviewer finds scope expansion, weakened gates, or secret exposure
merge target becomes ambiguous or dirty
slice completes but cannot be committed safely
```
