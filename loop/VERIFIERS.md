# Loop Verifiers

These commands verify Spec 222 contract slice `222.14 Corrective Wave Contract`.

## Contract Reads

```bash
/opt/homebrew/bin/rtk rg -n "222\\.14|Corrective Wave|Event Sequence|Aggregate Eval|Autonomous Worker|Live Gate|Idempotency" specs/222-ai-assistant-general-harness-mvp loop
```

## Scope Guard

```bash
/opt/homebrew/bin/rtk sed -n '220,330p' specs/222-ai-assistant-general-harness-mvp/spec.md
/opt/homebrew/bin/rtk sed -n '348,445p' specs/222-ai-assistant-general-harness-mvp/plan.md
/opt/homebrew/bin/rtk sed -n '665,890p' specs/222-ai-assistant-general-harness-mvp/tasks.md
/opt/homebrew/bin/rtk sed -n '70,95p' loop/CURRENT.md
```

Expected result: in the 222.14 contract ranges, sandbox/HA/production terms may
appear only as explicit non-goals or human gates.

## Static And Diff

```bash
/opt/homebrew/bin/rtk git diff --check
/opt/homebrew/bin/rtk git diff --stat
```

## Checker And Reviewer

Checker must verify:

```text
222.14 is split into five objective corrective slices.
Each slice has in-scope/out-of-scope boundaries, pass criteria, and evidence paths.
Sandbox isolation is explicitly excluded from this corrective wave.
Live gate missing credentials become env-blocked/waiting-human, not PASS.
Durable idempotency/circuit breaker is docs-only and separate from implementation.
```

Reviewer must verify:

```text
Diff scope is docs/loop only.
No code, tests, dependency, schema, or production behavior changed.
No secrets are committed.
No claim says 222.14 implementation is complete.
```
