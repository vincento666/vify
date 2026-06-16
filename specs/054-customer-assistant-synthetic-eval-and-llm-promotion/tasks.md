# Tasks 054: Customer Assistant Synthetic Eval And LLM Promotion Readiness

## 054.0 Sign-off

- [x] Confirm 054 uses synthetic data because there is no production traffic.
- [x] Confirm default gates make zero live LLM calls.
- [x] Confirm Chatflow/SOP data readiness is evaluated against the active
      database strategy, including the MySQL 8 migration path.
- [x] Confirm 054 only decides readiness for 055 and does not promote LLM output
      into the main path.
- [x] Confirm shadow mode is evidence-only: no ledger mutation, worker dispatch,
      proposed-action creation, or runtime response selection.

## 054.1 Synthetic Dataset

- [x] RED: eval test fails because synthetic case fixture coverage is missing.
- [x] Add deterministic synthetic customer-assistant cases.
- [x] Cover refund, baggage, combined, ambiguous, cancellation, operator,
      system, high-risk action, and worker failure scenarios.
- [x] Add case metadata for expected task keys, action states, and event types.

## 054.2 Promotion Report

- [x] RED: report test fails because pass-rate fields are missing.
- [x] Add promotion report builder.
- [x] Include task recognition, recommendation, safety, schema failure,
      fallback, event coverage, and live model call counts.
- [x] Include Chatflow/SOP data readiness status.
- [x] Ensure default report has `liveModelCalls=0`.
- [x] Prove LLM-shadow candidate output is exported as diff/eval evidence only.

## 054.3 Chatflow Data Readiness

- [x] RED: readiness test fails when a configured SOP binding points to a
      missing Chatflow row.
- [x] Add readiness probe for required SOP keys.
- [x] Support explicit fallback mock mode as a valid demo strategy.
- [x] Document MySQL 8 seed/import expectations.

## 054.4 Optional Live Batch

- [x] Add opt-in live LLM batch runner guarded by explicit env/config.
- [x] Record skipped evidence when env/config is unavailable.
- [x] Persist sample outputs without leaking credentials.

## 054.5 Browser UAT

- [x] Run operator panel Browser UAT for at least five synthetic scenarios.
- [x] Save screenshots and notes under `artifacts/slices/054-customer-assistant-synthetic-eval-and-llm-promotion/054.5/`.
- [x] Verify task ledger, progress checklist, recommendation, draft, proposed
      actions, and event timeline are visible.
- [x] Record Chatflow data strategy used during UAT.

## 054.6 Decision

- [x] Produce go/no-go recommendation for Spec 055.
- [x] If no-go, list the smallest blocking fixes.
