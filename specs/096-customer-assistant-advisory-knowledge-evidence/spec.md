# Spec 096: Customer Assistant Advisory Knowledge Evidence

## Goal

Make operator follow-up answers explainable in the customer assistant workbench.
When the operator asks an internal question, the workbench should show that the
recommendation was built from the current task ledger, runtime events,
SOP/Chatflow evidence, and seeded knowledge snippets.

## Acceptance Criteria

- `operator_advisory_context_packed` events are projected into a dedicated
  operator evidence panel.
- The panel shows task count, event count, SOP evidence count, knowledge snippet
  count, and context warnings.
- The panel does not render raw customer messages, phone numbers, order numbers,
  or knowledge snippet bodies.
- Empty sessions render an explicit empty state.
- Browser UAT verifies the panel after an operator follow-up question on a
  seeded demo story.

## Non-goals

- Do not change advisory recommendation generation.
- Do not add live RAG/vector retrieval in this slice.
- Do not expose raw knowledge snippets in the compact operator panel.

## Evidence

Evidence lives under
`artifacts/slices/096-customer-assistant-advisory-knowledge-evidence/096.1/`.
