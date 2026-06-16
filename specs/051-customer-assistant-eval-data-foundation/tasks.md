# Tasks 051: Customer Assistant Eval Data Foundation

## 051.0 Spec Sign-off

- [x] Confirm 051 creates the data path and initial golden cases, not a large
      production eval dataset.
- [x] Confirm default gates do not require live LLM calls.

## 051.1 Eval Schemas

- [x] Define task recognition, recommendation, safety, and timing case schemas.

## 051.2 Event Exporter

- [x] Export 047/048 event payloads into candidate cases.
- [x] Redact sensitive fields.

## 051.3 Golden Cases

- [x] Add handwritten cases for refund, baggage, refund+baggage, missing-field,
      and unsafe action.

## 051.4 Runner And Report

- [x] Add deterministic runner.
- [x] Emit report artifact.

## 051.5 Acceptance

- [x] Run eval gates and save report evidence.

## Evidence

- RED: `artifacts/slices/051-customer-assistant-eval-data-foundation/051.1/red.txt`
- Focused unit: `artifacts/slices/051-customer-assistant-eval-data-foundation/051.1/unit.txt`
- Customer-assistant unit pack: `artifacts/slices/051-customer-assistant-eval-data-foundation/051.5/backend.txt`
- Deterministic report: `artifacts/slices/051-customer-assistant-eval-data-foundation/051.5/report.json`
