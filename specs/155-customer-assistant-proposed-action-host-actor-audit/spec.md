# 155 Customer Assistant Proposed Action Host Actor Audit

## User Story

As a demo operator working in an embedded host shell, I need proposed-action confirmation, rejection, execution, and delivery audit records to identify the real host actor instead of collapsing every action to a generic `operator`.

## Acceptance Criteria

1. Proposed-action confirm events use the host `X-Hify-Actor-Id` when present.
2. Proposed-action reject events use the host `X-Hify-Actor-Id` when present.
3. Proposed-action execute lifecycle events use the host `X-Hify-Actor-Id` when present.
4. Operator audit rows expose the same actor as the underlying events.
5. Local/default requests preserve the current `operator` actor for backwards compatibility.

## Out Of Scope

- New permission model.
- UI actor picker.
- Changing action executor semantics.
