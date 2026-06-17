# Feature Spec: Customer Assistant Model Fallback Recovery Hints

## Status

Complete.

## User Story

As a customer-assistant operator, when the live or primary LLM path falls back
because of schema failure, low confidence, provider failure, or two-stage
validation mismatch, I can see a product-readable recovery hint in the
workbench instead of reading raw timeline payloads.

## Functional Requirements

- Derive model recovery hints from existing `llm_primary_fallback` and
  `two_stage_fallback` event evidence.
- Render the hints inside the existing evaluation/observability panel.
- Each hint must include:
  - the fallback phase;
  - sanitized fallback reason;
  - a recommended operator action;
  - a connection to the existing retry path when failed tasks are present.
- Do not change LLM selection, fallback policy, or model output validation.
- Do not expose raw prompts, raw customer text, API keys, phone numbers, or raw
  provider payloads.
- Runtime timeline payload previews and metrics failure summaries must use the
  same redaction boundary as the eval panel.

## Non-Goals

- No backend API changes.
- No live provider behavior changes.
- No automatic task mutation or auto-retry.
- No new database tables.

## Acceptance Criteria

- RED frontend view-model/panel tests fail before implementation because
  recovery hints do not exist.
- RED redaction tests fail before implementation when event timeline or metrics
  failure rows expose a raw customer phone number.
- Focused frontend tests pass after implementation.
- Browser UAT proves a session with model fallback evidence shows recovery
  hints, the task ledger still exposes the retry entrance for a failed task, and
  no raw customer phone number is visible anywhere on the page.
- `remScaleClosure`, full frontend unit, and frontend build pass.

## Evidence

Evidence lives under
`artifacts/slices/149-customer-assistant-model-fallback-recovery-hints/149.1/`.

- RED frontend: `red-frontend.txt`
- RED event timeline redaction: `red-event-timeline-redaction.txt`
- RED metrics failure redaction: `red-metrics-failure-redaction.txt`
- Focused frontend: `frontend-focused.txt`
- Frontend rem gate: `rem.txt`
- Full frontend unit: `frontend-full.txt`
- Frontend build: `frontend-build.txt`
- Browser UAT: `browser-uat.txt`
- Screenshot: `screenshots/model-fallback-recovery.png`
