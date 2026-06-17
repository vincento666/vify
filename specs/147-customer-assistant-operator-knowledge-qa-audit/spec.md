# Feature Spec: Customer Assistant Operator Knowledge Q&A Audit

## Status

Complete.

## User Story

As a customer-assistant operator or demo reviewer, when I ask an internal
knowledge/context question, the workbench records a sanitized audit and event
trail showing that the question was answered from session context, task ledger,
SOP evidence, and knowledge sources.

## Functional Requirements

- `POST /api/v1/customer-assistant/sessions/{session_id}/operator-knowledge-qa`
  must still return the Q&A payload added in 109.
- After a successful answer, the backend must append an
  `operator_knowledge_qa_answered` event with a compact sanitized payload.
- The event payload must include only safe summary fields:
  - sanitized question excerpt;
  - source count and primary source title/type;
  - evidence count;
  - warning count;
  - task count and pending action count.
- The event must appear in the existing operator audit projection.
- The Q&A path remains task-ledger read-only: task rows and proposed actions are
  not created, deleted, or transitioned by the Q&A call.
- The frontend runtime must refresh session events, metrics, proposed actions,
  tasks, and operator audit after a successful Q&A so the workbench shows the
  audit/observability row without a manual reload.

## Privacy And MySQL Scope

- The audit row and event payload must be sanitized by existing redaction
  helpers and must not expose phone numbers, order numbers, host context,
  provider keys, tool arguments, or raw payload dumps.
- Tests must run on the MySQL8 disposable test database helpers. No SQLite
  fallback is allowed.

## Non-Goals

- Changing knowledge retrieval scoring.
- Writing Q&A answers into the customer conversation lane.
- Mutating task status, proposed-action status, or worker runs.
- Adding a new table.

## Acceptance Criteria

- RED integration test fails before implementation because no
  `operator_knowledge_qa_answered` event/audit row exists.
- Green integration/API test proves event and audit rows are persisted,
  sanitized, and task rows are unchanged.
- Frontend runtime test proves a successful Q&A refreshes ledgers and keeps the
  answer visible.
- Focused backend, frontend, ruff, rem, E2E, and browser UAT evidence is saved.

## Evidence

Evidence lives under
`artifacts/slices/147-customer-assistant-operator-knowledge-qa-audit/147.1/`.

- RED backend: `red-backend.txt`
- RED frontend: `red-frontend.txt`
- Backend focused: `backend-focused.txt`
- Frontend focused: `frontend-focused.txt`
- Ruff: `ruff.txt`
- Frontend rem gate: `rem.txt`
- Frontend unit: `frontend-unit.txt`
- Browser E2E/UAT: `browser-uat.txt`
- Screenshot: `screenshots/operator-knowledge-qa-audit.png`

## Completion Evidence

- Backend focused: MySQL8 disposable integration and audit tests passed.
- Backend regression: customer-assistant contract plus unit tests passed.
- Frontend focused: customer-assistant API/runtime/view-model/panel tests passed.
- Frontend full unit: 91 files / 364 tests passed.
- Frontend build passed.
- Browser UAT passed with screenshot and audit-row assertion.
