# Spec 083: Customer Assistant Retry Recovery UAT

## Goal

Prove the operator workbench exposes a failed-task retry recovery path through
visible controls and the proposed-action safety boundary.

## Acceptance Criteria

- Browser UAT starts from a customer turn that renders a `FAILED` task.
- The failed task exposes a visible `重试` control only in the operator task
  ledger.
- Clicking `重试` posts `controlType: retry` to the task-control proposal API.
- The workbench refreshes ledgers and renders a pending `PROPOSED_TASK_COMMAND`
  retry action.
- The operator-facing metrics still show the failed task reason and pending
  action count.

## Non-goals

- Do not implement real retry execution in this slice.
- Do not change backend retry semantics.
- Do not change Vue/CSS styling unless the UAT exposes a real product defect.

## Evidence

Evidence lives under
`artifacts/slices/083-customer-assistant-retry-recovery-uat/<slice>/`.
