# Loop Verifiers

These commands verify the Spec 188/190 corrective contract revision. This unit
changes documentation/state only; implementation TDD starts at 188.4.

## Contract Content

    rtk rg -n "MEMORY.md|30 calendar days|100 tokens|three unprocessed|COMPLETED|batch.*hash|daily scheduler" specs/188-ai-assistant-prompt-skills-memory-compaction
    rtk rg -n "model call|session|cumulative|provider|model|cache read|reasoning|pricing_version|unknown|heatmap|Token/Cost" specs/190-ai-assistant-observability-benchmark
    rtk rg -n "Superseded|Not Implemented|Not Planned" specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md specs/190-ai-assistant-observability-benchmark/tasks.md

## Scope And Consistency

    rtk rg -n "\[ \]" specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md specs/190-ai-assistant-observability-benchmark/tasks.md
    rtk git diff --name-only e2024c11 -- specs/188-ai-assistant-prompt-skills-memory-compaction specs/190-ai-assistant-observability-benchmark specs/README.md loop/CURRENT.md loop/STATE.md loop/VERIFIERS.md
    rtk git diff --check

Expected:

- unchecked tasks exist only in 188.4-188.7 and 190.3-190.6;
- 188.2 and old 190 broad backlog are explicitly superseded/not planned, not
  falsely marked implemented;
- no source, schema, migration, tests, frontend, dependency, secret, or
  customer-assistant file belongs to this contract revision;
- Spec 188/190 and specs index describe the same execution order.

## Checker

Checker must verify:

- user decisions are represented exactly;
- goals, scope/non-goals, identity, API/UI contracts, acceptance, evidence,
  capabilities, authority, and stop rules are complete;
- MEMORY.md crash/idempotency and token aggregation semantics are testable;
- each future code slice has a RED plan and applicable gate;
- diff check passes.

## Reviewer

Reviewer must verify:

- historical completed work is preserved without making old pending tasks look
  complete;
- MEMORY.md remains the only memory content truth source;
- isolation does not trust arbitrary client paths;
- DB/file crash windows, concurrency, date bounds, token cap, pricing version,
  unknown cost, streaming calls, and cache/reasoning totals are covered;
- 190 does not expand into benchmark, governance, alerts, budget, billing, or
  cross-user admin;
- no unrelated dirty diff is staged or committed with this unit.
