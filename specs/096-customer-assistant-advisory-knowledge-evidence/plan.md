# Plan 096

## 096.1 Operator Advisory Evidence Panel

- Capture RED frontend tests for missing advisory evidence projection.
- Capture RED backend test for missing seeded SOP/Chatflow advisory evidence.
- Add a view-model formatter for `operator_advisory_context_packed` events.
- Add fallback SOP/Chatflow advisory evidence from task worker/checkpoint state.
- Render a compact operator advisory evidence panel.
- Add browser UAT for an operator knowledge-backed follow-up.

## Gates

- RED frontend test before implementation.
- RED backend test before implementation.
- Green focused backend advisory integration test.
- Green focused customer-assistant frontend tests.
- Green frontend rem gate, full frontend unit, and build.
- Green browser UAT with screenshot evidence.
