# Spec 113: Customer Assistant Observability Eval Surface

## Status

Slice 113.1 implemented and verified. Commit deferred because the touched
customer-assistant frontend files also contain concurrent Q&A UI lane changes;
main integration should stage the observability hunks together with the owning
lane or split them deliberately.

## Goal

Strengthen the productized MVP demo by giving operators one compact,
product-readable observability/eval panel for the active customer-assistant
session. The panel should connect task recognition, worker execution,
recommendation model evidence, adoption metrics, and failure reasons without
requiring raw timeline inspection.

## Functional Requirements

- Build the eval surface from existing customer-assistant session data:
  tasks, events, metrics, proposed actions, recommendation state, and worker
  profile evidence already loaded by the workbench.
- Show per-session task recognition hits, including task key/type and worker
  route.
- Show worker execution evidence, including started/result/failed event counts
  and current task status distribution.
- Show recommendation/model evidence from existing LLM shadow, primary,
  two-stage fallback, or two-stage primary events.
- Show hit/adoption metrics using existing human-confirmation metrics.
- Show recent failure reasons in the same product-readable panel.
- Keep the panel secret-safe: do not surface raw event payloads, raw customer
  text, phone numbers, API keys, or full model baseline/shadow bodies.

## Non-Goals

- Do not add operator Q&A controls or change the Q&A UI lane.
- Do not change backend knowledge-QA, Runtime Lab, workflow runtime, seed,
  MySQL, live acceptance core, or worker-profile configuration behavior.
- Do not add a new backend endpoint unless existing loaded data is insufficient.
- Do not change task recognition, worker scheduling, model selection, or action
  execution semantics.

## Acceptance Criteria

- RED frontend unit evidence proves the eval-surface view-model is missing.
- The view-model aggregates task recognition, worker execution, model
  diff/fallback evidence, adoption metrics, and failure reasons from existing
  data.
- The workbench renders a dedicated read-only eval/observability panel for the
  active session.
- Focused frontend tests pass.
- Frontend rem gate passes because this slice touches UI styling.
- Browser UAT captures the panel with seeded/demo session evidence.

## Evidence

Evidence lives under
`artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/`.

- RED frontend:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/red.txt`
- Focused frontend view-model:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/frontend-viewmodel.txt`
- Focused frontend panel:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/frontend-panel.txt`
- Combined focused frontend:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/frontend-focused.txt`
- Frontend rem gate:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/frontend-rem.txt`
- Unit scan:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/unit-scan.txt`
- Browser UAT report:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/uat-report.json`
- Browser UAT notes:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/uat.md`
- Browser UAT screenshots:
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/screenshots/eval-surface.png`
  and
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/screenshots/eval-surface-panel.png`
