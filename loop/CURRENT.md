# Current Loop Scope: Spec 188.7 Aggregate Acceptance

## Status

    mode: Closed Loop
    active spec: 188-ai-assistant-prompt-skills-memory-compaction
    active slice: 188.7 Aggregate Acceptance
    phase: COMPLETE
    TDD method: tdd (acceptance replay; no production behavior planned)

## Contract

    specs/188-ai-assistant-prompt-skills-memory-compaction/spec.md
    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md

Acceptance:

- replay the required 188.4-188.6 gates on the combined implementation;
- prove the DB stores cursor metadata, never memory text;
- prove the reader remains heading-based and no legacy JSON memory writes return;
- prove frontend, customer-assistant, daily scheduler, and Spec 189 stayed out of scope;
- record Checker, Reviewer, evidence, and residual risks.

## Worktree

    branch: codex/spec-188-memory-md
    path: /Users/vincento/work/develop/hify-spec-188-memory-md
    base: 8f50a1bb
    merge target: codex/runtime-v2-production-upgrade
    dirty before slice: no

## Frozen Scope

Allowed:

    specs/188-ai-assistant-prompt-skills-memory-compaction/tasks.md
    loop/CURRENT.md
    loop/STATE.md
    loop/VERIFIERS.md
    artifacts/slices/188-ai-assistant-prompt-skills-memory-compaction/188.7/

Production or test edits require reopening the relevant implementation slice.

## Stop Conditions

Stop and reopen implementation if any required gate fails, memory text appears
in DB, fixed tail reads or legacy JSON writes return, or an excluded module was
changed by Spec 188 commits.
