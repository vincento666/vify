# Spec 081: Proposed Action Transition Hardening

## Goal

Make proposed-action lifecycle transitions safe for product demo concurrency:
normal actions must not be executed twice if two operator requests race after
confirmation.

## Acceptance Criteria

- Repository status transitions can require an expected current status and do
  not update stale rows.
- `execute_action` claims `CONFIRMED -> EXECUTING` atomically before invoking
  the executor.
- A stale or duplicate execute request returns a clear bad-request response and
  does not call the executor again.
- Existing confirm/reject/task-command semantics remain compatible.
- Failed executor results still persist `error`, `audit`, and
  `proposed_action_failed` evidence.

## Non-goals

- Do not change task-command confirmation semantics; task commands still apply
  on confirm.
- Do not introduce real external write tools.
- Do not change frontend action labels in this slice.

## Evidence

Evidence lives under
`artifacts/slices/081-proposed-action-transition-hardening/<slice>/`.
