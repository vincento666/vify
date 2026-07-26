# 228.4 TDD Preflight

- method: `tdd`
- branch: `codex/spec-228-runtime-lab-intent-routing-reliability-560c`
- start HEAD: `eb4f4a869c7c3e501ad020bfa957fcfe0d81aa34`
- worktree: clean
- MySQL: existing compose `mysql8` healthy
- live / paid provider calls: `0`
- repair budget: `3`

## Baseline

- backend focused: PASS — `5 passed`, `17 subtests passed`
- frontend focused: initial `ENV-BLOCKED-228.4-FRONTEND-DEPS` because `vitest`
  was absent; recovered with the existing lockfile via `npm --prefix frontend ci`
- frontend focused after recovery: PASS — `15 passed`

## Observable RED

Add tests before production code proving:

1. a normalized targeted classifier question is the assistant reply;
2. `clarificationQuestion` survives public route payload, decision event, stored
   idempotent command replay, and evaluation replay;
3. missing / blank / invalid question uses only the existing generic menu;
4. clarification creates no task and invokes no child SOP adapter;
5. the inspector exposes the additive nullable field.

Expected RED: `RouteDecision` has no `clarification_question`, serializers omit
`clarificationQuestion`, and the normal CLARIFY reply is always the generic
menu.

## Frozen Boundaries

- additive API field only; envelope and SSE event types unchanged;
- no schema migration;
- no live provider;
- Chatflow remains execution-state truth;
- no candidate fusion, execution authorization, or composite intent work.
