# Plan: Customer Assistant Observability Eval Surface

## Slice 113.1

Status: implemented and verified; commit deferred due shared frontend file
overlap with the Q&A UI lane.

Use the existing frontend runtime state rather than adding backend API surface.
The session already loads tasks, events, metrics, proposed actions, worker
profiles, and recommendation state, which is enough to produce a compact eval
summary.

## Design

- Add a focused `formatCustomerAssistantEvalSurface` view-model formatter in
  `frontend/src/views/customerAssistant/customerAssistantViewModel.ts`.
- The formatter will produce:
  - KPI tiles for recognized task hits, worker evidence, model evidence, and
    adoption.
  - Recognition rows derived from existing `task_recognized` evidence.
  - Worker rows derived from task rows and worker event counts.
  - Model rows derived from `llm_shadow_diff_recorded`,
    `llm_primary_fallback`, `llm_primary_selected`, `two_stage_fallback`, and
    `two_stage_primary_selected` events.
  - Failure rows from existing metrics.
- Add a read-only panel to
  `frontend/src/views/customerAssistant/CustomerAssistantPanel.vue`.
- Keep output compact and redacted; do not render raw event payload JSON in the
  eval panel.

## Testing

- RED: add a frontend unit test for the missing formatter and save failure
  output to `red.txt`.
- GREEN: implement the formatter and panel with focused tests.
- Run:
  - focused customer-assistant view-model/panel tests;
  - `src/remScaleClosure.test.ts`;
  - browser UAT with screenshot and report.

## Risks

- Existing event payloads may vary by runtime mode. The model evidence parser
  should be tolerant and produce useful fallback labels instead of failing.
- The panel must avoid surfacing raw payload bodies. Only compact reason,
  verdict, phase, source, and count fields are allowed.
