# Spec 190: AI Assistant Observability Benchmark

## Status

Slice `190.0` documentation sign-off is complete. Slice `190.1` backend
observability tracer is complete for inspector observability snapshots and a
deterministic benchmark status.

## Goal

Add the first PRD Phase 7 observability and benchmark layer for the AI
Assistant harness:

```text
run + events + tool calls + approvals
  -> observability snapshot
  -> usage placeholders and elapsed time
  -> deterministic benchmark status
  -> inspector payload
```

## Scope

In scope:

- backend observability snapshot builder;
- event/tool/approval counts;
- elapsed time and token placeholders;
- deterministic benchmark name, metrics, thresholds, and pass/fail flag;
- inspector API payload exposure;
- MySQL8-backed contract tests;
- no frontend visual changes.

Out of scope:

- real token/cost accounting;
- live LLM benchmark gates by default;
- frontend dashboards;
- cross-run governance policy engine;
- SQLite/PostgreSQL persistence paths;
- customer-assistant runtime changes.

## Acceptance Criteria

- RED evidence shows missing observability module and inspector payload.
- Inspector includes `observability` with run id, status, counts, usage, and
  benchmark snapshot.
- Existing `usage` field remains available for the current frontend.
- Existing AI Assistant kernel/inspector contracts remain green.
- Default tests are deterministic and credential-free.
- Future real LLM benchmarks must be optional and OpenRouter env-gated.

