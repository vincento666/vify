# Current Loop Scope: Runtime V2 Production Closure

## Status

Active implementation sprint:

```text
213+ Runtime V2 Target Gap Closure (in-progress)
```

## Active Specs

Spec range:

```text
213-runtime-async-default-invocation-gateway
214-runtime-dag-multipath-semantics
215-runtime-dag-frontier-scheduler
216-chatflow-sop-compat-on-dag
217-runtime-v2-node-compatibility-matrix
218-runtime-production-job-scheduler
219-runtime-event-cancel-ratelimit-backpressure
220-runtime-observability-ops-module
221-runtime-capacity-fault-acceptance
```

Canonical target:

```text
docs/chatflow-workflow-production-upgrade.md
```

Replay contract:

```text
artifacts/slices/runtime-v2-closure-replay/replay-contract.md
```

## Worktree

```text
branch: codex/runtime-v2-closure-replay
path: /Users/vincento/work/develop/hify-runtime-v2-closure-replay
base: d6fc969c feat(ai-assistant): complete harness MVP gates
merge target: codex/runtime-v2-production-upgrade
source replay branch: codex/runtime-v2-specs-213-plus
```

This worktree is isolated to protect completed spec 222+ changes while closing
runtime 213-221 target gaps.

## Frozen Scope

Allowed:

```text
runtime 213-221 code, tests, docs, evidence, loop state
runtime-lab SOP async default and runtime state boundary fixes
Runtime Ops, runtime job, DAG scheduler, event/cancel/backpressure, capacity evidence
222 regression smoke and protected-path guards
```

Protected:

```text
app/modules/ai_assistant/
frontend/src/views/aiAssistant/
specs/222-ai-assistant-general-harness-mvp/
tests/*ai_assistant*
```

## Stop Conditions

Stop and enter `waiting-human` if:

```text
222 protected-path diff is non-empty
222 smoke fails due runtime replay/fix
scope needs new dependency, production secret, release, push, or irreversible action
target requires real external service not available locally
same verifier failure repeats twice without narrower hypothesis
Reviewer finds scope expansion, weakened tests, or missing evidence
merge target becomes ambiguous or dirty
```
