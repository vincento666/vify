# 085 Customer Assistant Confirmed Retry Worker Recovery

## Goal

When an operator proposes and confirms a retry command for a failed customer
assistant task, confirmation must produce deterministic recovery evidence
instead of only mutating the task ledger. A confirmed retry should dispatch a
fresh worker attempt when the task is worker-runnable, then expose the resulting
task status, worker run refs, and event trail through the existing
`/api/v1/customer-assistant/...` APIs.

## Acceptance Criteria

- A failed task can still be retried only through the existing task-control
  proposal and proposed-action confirmation flow.
- Confirming the proposed retry command dispatches a fresh worker attempt for
  ready retry tasks.
- Deterministic workers that complete during confirmation update the task to
  `COMPLETED`, persist `lastResult`, and expose supported worker refs.
- The event stream records operator-visible recovery evidence including
  `task_control_proposed`, `proposed_task_command_confirmed`, `task_started`,
  `worker_started`, and `task_completed`.
- Cancelled task controls remain ledger-only and do not dispatch workers.
- Existing API envelope and product wording remain unchanged.

## Non-goals

- No frontend visual changes.
- No workflow runtime changes.
- No edits to specs `080` or `084`.
- No real RAG, real tool calling, or MCP expansion.

## Evidence

Slice evidence lives under
`artifacts/slices/085-customer-assistant-confirmed-retry-worker-recovery/085.1/`.
