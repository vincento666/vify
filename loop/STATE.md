# Loop State

## Current

- date: 2026-07-11
- mode: Contract Gate
- active contracts: Spec 188 corrective MEMORY.md scope; Spec 190 token/cost
  scope
- current unit: contract revision
- implementation: not started
- next code slice after gate: 188.4
- branch: codex/spec-222-14-5-idempotency-spec
- base: e2024c11
- merge target: codex/runtime-v2-production-upgrade
- worktree: dirty with unrelated existing changes
- oversight: human-on-the-loop; no new product decision currently missing

## Accepted Decisions

- Spec 189 will not be implemented.
- MEMORY.md is the only durable memory source.
- One MEMORY.md belongs to each trusted user/workspace scope.
- Reader defaults to last 30 calendar days and locates the bounded start line
  from strict date headings.
- Each day's entire memory block is capped at 100 tokens.
- Extraction runs after each three new COMPLETED runs across sessions.
- Daily scheduled tail flush is future scope.
- Spec 190 includes token/cost only.
- Usage is raw per model call, aggregated by session, total, and common
  dimensions.
- Dashboard follows accepted reference: cards, daily heatmap, session detail,
  provider/model and token-type views.

## Contract Evidence

- spec/plan/tasks rewritten for 188 and 190.
- old 188.2 unchecked JSON-memory tasks moved to explicit superseded history.
- old broad 190 unchecked backlog moved to explicit not-planned history.
- specs/README.md natural order and directory index updated.
- git diff --check passed after initial rewrite.
- contract audit added crash-safe MEMORY.md cursor semantics and prevented
  cache/reasoning token double-count.
- independent Checker round2: ALL GREEN.
- independent Reviewer round1: PASS, medium residual implementation risk, no
  blocker.

## Current Gate

Contract content and independent review are complete. Closed Loop remains
blocked until:

1. contract files are selectively committed without unrelated dirty changes;
2. implementation branch/worktree/base/merge target are frozen.

## Next Action

Selectively commit contract scope, then enter 188.4 on isolated
codex/spec-188-memory-md worktree.

## Residual Risks

- current RequestContext is the host identity seam; implementation must prove
  production scope cannot be selected by an arbitrary memory path.
- DB cursor and filesystem replacement cross a transaction boundary; accepted
  batch/input/target hash recovery must be tested at each crash window.
- provider cache/reasoning semantics differ; per-provider normalizers must avoid
  total-token double-count.
