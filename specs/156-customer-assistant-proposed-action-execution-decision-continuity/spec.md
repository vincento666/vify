# 156 Customer Assistant Proposed Action Execution Decision Continuity

## User Story

As an operator reviewing a completed proposed action, I need the final action receipt to show both the execution result and the human confirmation decision that authorized it.

## Acceptance Criteria

1. Confirming a proposed action with a note stores a sanitized `result.decision.note`.
2. Executing the confirmed action preserves `result.decision`.
3. Executing the confirmed action still records executor output:
   - `executorRef`
   - `audit`
   - `error`
4. Rejected actions cannot be executed and do not emit executing/executed events.
5. Public action/event/audit surfaces remain sanitized.

## Out Of Scope

- New frontend receipt layout.
- New action executor implementations.
- Proposed action revision columns.
