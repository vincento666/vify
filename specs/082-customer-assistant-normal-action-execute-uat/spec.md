# Spec 082: Customer Assistant Normal Action Execute UAT

## Goal

Prove the operator workbench can complete a normal proposed-action lifecycle
through visible controls: confirm, enable execute, execute, and render terminal
status.

## Acceptance Criteria

- Browser UAT clicks `确认拟议动作` for a normal non-task-command action.
- The `执行已确认动作` button becomes enabled only after confirmation.
- Browser UAT clicks `执行已确认动作` and observes an `EXECUTED` action state.
- The script asserts the `/execute` API call happened exactly through the
  workbench flow.
- Existing local draft behavior remains API-free.

## Non-goals

- Do not change backend execution semantics in this slice.
- Do not add real external write tools.
- Do not redesign the proposed-action panel.

## Evidence

Evidence lives under
`artifacts/slices/082-customer-assistant-normal-action-execute-uat/<slice>/`.
