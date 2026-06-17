# Plan: Customer Assistant Reply Draft Proposed Action

## Slice 126.1

Bridge generated customer reply drafts into the existing human-confirmed draft
delivery outbox by creating a pending `send_customer_message` proposed action
from normal customer turns.

## Approach

1. Add a public API contract test that runs a customer turn, fetches proposed
   actions, confirms the generated reply action, delivers it, and verifies
   events/audit/redaction.
2. Add a narrow service helper after recommendation selection that upserts one
   reply-draft delivery action per run.
3. Refresh proposed action rows before returning the turn result so the action
   appears in the immediate response and ledgers.
4. Reuse existing repository idempotency and outbox delivery semantics.

## Test Strategy

- Focused contract:
  - `tests/contract/customer_assistant/test_customer_assistant_api.py`
- Existing delivery integration:
  - `tests/integration/customer_assistant/test_draft_delivery_outbox.py`
- Browser UAT:
  - Not repeated here; slice 124 already exercises the operator UI against a
    `send_customer_message` action. This slice proves normal backend generation
    creates the same action type and that public API confirm/deliver works.

## Risks

- Replays could duplicate actions if the key is not per run.
- Empty placeholder drafts should not create deliverable actions.
- Recommendation selection can replace drafts; the action should use the final
  selected draft, not an earlier baseline draft.
