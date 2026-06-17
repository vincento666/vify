# Plan: 147.1 Operator Knowledge Q&A Audit

## Slice

Add an audit/event trail to the existing 109/112 operator Q&A flow.

1. Extend the backend integration test to prove Q&A appends a sanitized
   `operator_knowledge_qa_answered` event and operator audit row while preserving
   task ledger rows.
2. Extend the frontend runtime test to prove successful Q&A refreshes ledgers
   and keeps the returned answer in state.
3. Implement the smallest backend event append and audit projection.
4. Refresh ledgers after successful frontend Q&A.
5. Update browser UAT to validate the audit row after asking the Q&A question.

## Backend Design

Use the existing `customer_assistant_event` table and `list_operator_audit`
projection. The Q&A event is session-scoped, source `operator_advisory`, actor
`operator`, and carries only compact sanitized counts/excerpts.

## Frontend Design

Reuse `refreshCustomerAssistantRuntimeLedgers(session.id)` after a successful
Q&A response. Rebuild derived workbench state from refreshed tasks/events/actions
and preserve `operatorKnowledgeQa`.

## Verification

- RED backend and frontend tests first.
- Focused backend integration for `test_operator_knowledge_qa.py`.
- Focused frontend runtime test for customer assistant Q&A.
- Ruff on touched backend/tests.
- `remScaleClosure` because Vue-visible workbench UAT is part of the slice,
  although this slice should not need CSS changes.
- Browser E2E with screenshot.
