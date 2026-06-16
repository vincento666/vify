# Tasks: Customer Assistant Observability Eval Surface

## Slice 113.1

- [x] Add RED frontend unit coverage for the eval-surface view-model.
- [x] Save RED evidence to
  `artifacts/slices/113-customer-assistant-observability-eval-surface/113.1/red.txt`.
- [x] Implement the eval-surface formatter in the customer-assistant view-model.
- [x] Render a read-only eval/observability panel in the customer-assistant
  workbench.
- [x] Add/update focused panel contract coverage.
- [x] Run focused frontend tests.
- [x] Run frontend rem gate.
- [x] Run browser UAT and save screenshot/report.
- [x] Update evidence paths and mark slice complete.

## Integration Note

Commit deferred: the same files also contain concurrent
`112-customer-assistant-operator-knowledge-qa-ui` changes. Do not stage blindly;
stage the 113 hunks intentionally or integrate after the Q&A lane lands.
