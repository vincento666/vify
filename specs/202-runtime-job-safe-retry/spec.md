# Spec 202: Runtime Job Safe Retry

## Goal

Allow a Workflow runtime job picked up after worker restart or lease takeover to
skip already completed nodes and continue from the next reliable node.

This completes the first practical recovery behavior required by Phase 7 of
`docs/chatflow-workflow-production-upgrade.md`.

## In Scope

- Rehydrate `ExecutionContext` from existing completed node runs for the active
  path.
- Continue execution from the first not-yet-completed node.
- Avoid duplicating completed node runs after worker restart/takeover.
- Keep failed or waiting nodes retried/resumed by existing runtime semantics.

## Out of Scope

- Exactly-once side effects for external API/tool/LLM calls.
- Branch merge reconciliation beyond the current selected path.
- Async resume/cancel jobs.
- Chatflow turn-level recovery.

## Acceptance Criteria

- A Workflow run with a completed first node and a queued runtime job can be
  completed by a later worker without re-running that first node.
- Existing runtime result/events/nodes APIs remain compatible.
- Normal fresh runs still execute from the first node after `start`.
