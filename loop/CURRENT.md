# Current Loop Scope: Spec 188/190 Corrective Contracts

## Status

    mode: Contract Gate
    current unit: 188/190 contract revision
    implementation: not started
    next implementation slice: 188.4 Scope Isolation And Markdown Store

Spec 189 is cancelled by user decision.

## Active Contracts

Primary:

    specs/188-ai-assistant-prompt-skills-memory-compaction/spec.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/plan.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md

Follow-on:

    specs/190-ai-assistant-observability-benchmark/spec.md
    specs/190-ai-assistant-observability-benchmark/plan.md
    specs/190-ai-assistant-observability-benchmark/tasks.md

## Frozen Outcome

Spec 188:

- one canonical MEMORY.md per trusted user/workspace;
- rolling 30-day heading-based bounded read;
- each dated day's full block at most 100 tokens;
- model extraction after each batch of three new COMPLETED runs across sessions;
- DB stores cursor/recovery metadata only, never memory text;
- no daily scheduler in this wave.

Spec 190:

- one scoped immutable ledger row per model call;
- session, cumulative, date, provider, model, and token-type aggregation;
- provider actual cost, then versioned estimate, then explicit unknown;
- Token/Cost dashboard with cards, heatmap, filters, session details, and
  distributions;
- no benchmark, governance, alerts, budget enforcement, billing, or cross-user
  admin expansion.

## Contract Evidence

    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/contract-revision/

Required before Closed Loop:

- contract consistency verifier passes;
- independent Checker result exists;
- independent Reviewer finds no blocker;
- contract-only changes are isolated from unrelated dirty files;
- implementation branch/worktree/base/merge target are recorded.

## Branch Preflight

    worktree: /Users/vincento/work/develop/hify
    branch: codex/spec-222-14-5-idempotency-spec
    contract base: e2024c11
    merge target: codex/runtime-v2-production-upgrade
    dirty: yes; unrelated loop/host changes exist

Do not begin implementation in this mixed dirty worktree. After contract review,
selectively commit only contract-scope files, then create an isolated
codex/spec-188-memory-md implementation branch/worktree from that commit.

## Contract-Revision Scope

Allowed:

    specs/188-ai-assistant-prompt-skills-memory-compaction/
    specs/190-ai-assistant-observability-benchmark/
    specs/README.md
    loop/CURRENT.md
    loop/STATE.md
    loop/VERIFIERS.md
    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/contract-revision/

No source, schema, migration, test, frontend, dependency, secret, or
customer-assistant changes are authorized in this unit.

## Stop Conditions

Stop and remain in Open Loop/Waiting Human if:

- trusted workspace identity requires arbitrary client paths;
- user/workspace isolation cannot be enforced through the host boundary;
- compatibility requires removing a public API field;
- memory needs a second durable content store;
- cost semantics require billing, budget, or governance decisions;
- global settings/admin information architecture becomes necessary;
- branch/base/merge target remains ambiguous after contract review.
