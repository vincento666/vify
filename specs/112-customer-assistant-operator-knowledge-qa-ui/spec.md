# Feature Spec: Customer Assistant Operator Knowledge Q&A UI

## Status

Complete.

## User Story

As a customer-assistant operator, I can ask a read-only knowledge/context
question from the workbench and see a concise answer with sources, task
evidence, warnings, and a compact session context summary.

## Functional Requirements

- Add a frontend API client for
  `POST /api/v1/customer-assistant/sessions/{session_id}/operator-knowledge-qa`.
- Add workbench runtime state for submitting one operator question against the
  current session without changing task, event, action, metric, or audit
  ledgers.
- Render the answer inside the existing operator panels.
- Show sources, evidence, warnings, and context summary as compact operator
  rows.
- Keep raw endpoint payloads out of the UI. In particular, do not expose raw
  event payloads, host context, full customer identifiers, or JSON dumps in the
  Q&A panel.
- If no session is loaded yet, keep the submit control unavailable and explain
  that a demo story or turn is required first.

## Scope

- `frontend/src/api/customerAssistant.ts`
- `frontend/src/views/customerAssistant/customerAssistantRuntime.ts`
- `frontend/src/views/customerAssistant/customerAssistantViewModel.ts`
- `frontend/src/views/customerAssistant/CustomerAssistantPanel.vue`
- Focused customer-assistant frontend tests and E2E/UAT files under
  `frontend/e2e/customer-assistant-*`
- This spec folder and evidence under
  `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/`

## Non-Goals

- Backend changes.
- Runtime Lab, workflow runtime, seed, live acceptance, MySQL persistence, or
  demo bootstrap changes.
- Real pgvector/RAG behavior beyond the backend endpoint added in 109.
- Sending Q&A answers to the customer lane.

## Acceptance Criteria

- RED frontend test fails before implementation and is saved as
  `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/red.txt`.
- Focused customer-assistant API/runtime/view-model/panel tests pass after the
  implementation.
- `remScaleClosure` passes after any Vue/CSS edits.
- Browser UAT opens `/customer-assistant`, asks an operator knowledge question,
  and captures the answer/sources/evidence/warnings/context summary without raw
  payload leaks.
- Full changed-scope evidence is saved under the 112.1 artifact directory.

## Evidence

- RED: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/red.txt`
- Focused frontend/API: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/frontend.txt`
- Customer-assistant unit: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/customer-assistant-unit.txt`
- Full frontend unit: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/frontend-full.txt`
- Frontend rem gate: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/rem.txt`
- Browser E2E output: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/e2e.txt`
- Browser UAT: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/uat.md`
- Browser screenshot: `artifacts/slices/112-customer-assistant-operator-knowledge-qa-ui/112.1/screenshots/operator-knowledge-qa.png`
