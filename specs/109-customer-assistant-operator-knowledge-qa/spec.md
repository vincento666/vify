# Feature Spec: Customer Assistant Operator Knowledge Q&A

## Status

Complete.

## User Story

As a customer-assistant operator, I can ask a read-only question about the
current customer session and receive a concise answer grounded in the current
customer context, task ledger, proposed-action ledger, and seeded FAQ/knowledge
context.

## Functional Requirements

- Add a backend API for operator knowledge Q&A scoped to one customer-assistant
  session.
- The response must include:
  - `answer`: deterministic answer text suitable for the operator.
  - `sources`: knowledge/FAQ sources used to answer the question.
  - `evidence`: task/SOP/Chatflow evidence derived from the current ledger.
  - `contextSummary`: compact session, customer, task, and action summary.
- The Q&A path must be read-only and must not create, update, delete, or
  transition customer task ledger rows.
- The Q&A path should prefer seeded FAQ/knowledge results through the existing
  knowledge facade when knowledge base ids are present on the session.
- Missing knowledge context must return an explicit warning rather than
  mutating state or fabricating a source.

## Scope

- Backend customer-assistant service, schema, and router only.
- Integration/unit tests under `tests/integration/customer_assistant` or
  `tests/unit/customer_assistant`.

## Non-Goals

- Frontend UI changes.
- Runtime Lab, workflow runtime, seed, or live proposed-action acceptance
  changes.
- Real pgvector/RAG enhancements beyond the current knowledge facade behavior.
- Task-command proposal or action execution behavior changes.

## Privacy And Tenant Scope

- Session access must continue through the existing customer-assistant access
  dependency and service `_ensure_session` tenant guard.
- Returned session/customer context must be summarized and sanitized; raw
  `hostContext`, tokens, phone numbers, email addresses, and order-like ids must
  not be returned in plain text.
- Source and evidence payloads should be compact and avoid exposing raw event
  payloads.

## Acceptance Criteria

- RED integration test proves the operator Q&A API is absent or fails before
  implementation.
- Green integration/API test shows a seeded demo session answers a refund and
  baggage question from seeded FAQ context.
- The same test proves task ledger rows are unchanged after the Q&A request.
- Focused customer-assistant tests pass.
- Ruff passes for touched backend/test files.

## Evidence

Evidence lives under
`artifacts/slices/109-customer-assistant-operator-knowledge-qa/109.1/`.

- RED: `red.txt`
- Integration/API: `integration.txt`
- Focused unit/regression: `unit.txt`
- Ruff: `ruff.txt`
