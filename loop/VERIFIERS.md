# Loop Verifiers

These commands verify Spec 222 slice `222.14.5`.

## RED

```bash
/opt/homebrew/bin/rtk rg -n "operation_id|UNKNOWN|fallback|side-effect|read tools|circuit breaker|release authority" specs/224-ai-assistant-durable-toolrunner-idempotency
```

Expected RED before implementation:

```text
This is a docs-only slice; missing required semantic answers fail the docs checker.
```

## Focused Gates

```bash
/opt/homebrew/bin/rtk rg -n "operation_id|UNKNOWN|release authority|fallback|read tools|side-effect tools|Session/run|Durable Circuit Breaker" specs/224-ai-assistant-durable-toolrunner-idempotency/spec.md
/opt/homebrew/bin/rtk rg -n "224\\.1|224\\.2|224\\.3|224\\.4|224\\.5|224\\.6|224\\.7|224\\.8" specs/224-ai-assistant-durable-toolrunner-idempotency/tasks.md
```

## Static And Diff

```bash
/opt/homebrew/bin/rtk git diff --check
```

## Checker And Reviewer

Checker must verify:

```text
Spec 224 exists with spec/plan/tasks.
Spec answers key generation, UNKNOWN retention, release authority, fallback operation_id policy, and durable breaker state.
Tasks are implementable slices with RED tests.
No implementation code was changed.
```

Reviewer must verify:

```text
Diff scope is limited to docs/spec/loop state.
The new spec separates MVP and production boundaries.
It does not mix durable idempotency with sandbox, HA, multi-tenant infra, or business adapter work.
No code, schema, dependency, or secret was introduced.
```
