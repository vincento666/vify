# Tasks 067: Cross-runtime Observability And Regression Gate

## 067.0 Sign-off

- [x] Confirm 067 adds observability/gates, not new runtime semantics.
- [x] Confirm old API compatibility regressions block completion.
- [x] Confirm canvas/debug node state is projected from runtime v2 events.
- [x] Confirm missing evidence is shown as warnings.
- [x] Confirm SOP multi-level router compatibility regressions block completion.
- [x] Confirm correlation refs are mandatory across assistant/worker/runtime
      events.
- [x] Confirm UI/artifacts distinguish live, replayed, and compatibility-summary
      events.

## 067.1 Event Summary Mapping

- [x] RED: event summary test fails because runtime source is ambiguous.
- [x] Add source-aware event summary mapping.
- [x] Add correlation refs: assistant run, task, worker run, runtime run, source
      event.
- [x] Add live/replay/summary labels.
- [x] Preserve raw debug refs.

## 067.2 Operator Panel Evidence

- [x] Show assistant task progress.
- [x] Show worker progress/refs.
- [x] Show Chatflow/Workflow runtime progress summaries when present.
- [x] Show warnings for missing data or fallback.
- [x] Show failure/timeout/cancel states distinctly.
- [x] Show SOP router context and routed task refs when present.
- [x] Show waiting/blocking reason, required fields, node prompt, and
      checkpoint ref when a worker waits for input.
- [x] Redact sensitive payloads before rendering or exporting evidence.

## 067.3 Canvas Debug Evidence

- [x] RED: canvas debug state can drift from runtime v2 node status/events.
- [x] Show Workflow/Chatflow node running animation from `RUNNING` events.
- [x] Show completed, waiting, skipped, and failed node states from runtime v2
      status/events.
- [x] Update debug panel rows in real time as node events arrive.
- [x] Stop debug run UI on node failure and show failed node/error.
- [x] Prove reconnect restores node states from durable event replay.

## 067.4 Regression Gates

- [x] Add tests for legacy customer assistant.
- [x] Add tests for worker async state.
- [x] Add tests for Chatflow v2 live event and v1 fallback.
- [x] Add Workflow v2 tests if 065 is enabled.
- [x] Add Chatflow canvas debug v2 live node-status gate.
- [x] Add Workflow canvas debug v2 live node-status gate if 065 is enabled.
- [x] Add node failure stops run/debug UI regression gate.
- [x] Add waiting Chatflow node recommendation gate for `QUESTION`,
      `HUMAN_INPUT`, and `INFORMATION_COLLECTION`.
- [x] Add SOP router test for intent A -> intent B -> resume intent A.
- [x] Add SOP router test where one task uses Chatflow v2 and another task
      falls back to v1 in the same session.
- [x] Add latency/status/fallback summary artifact for UAT comparison.

## 067.5 Browser UAT

- [x] Run UAT matrix and save notes/screenshots.
- [x] Confirm timeline distinguishes assistant/worker/chatflow/workflow sources.
- [x] Confirm Workflow/Chatflow canvas animation and completed/failed states
      match runtime v2 node events.
- [x] Confirm debug panel receives real-time node status updates.
- [x] Confirm a node error stops the run and surfaces failure.
- [x] Confirm waiting node prompt appears in customer draft and operator
      recommendation evidence.
- [x] Confirm trace refs can navigate from recommendation to worker/runtime
      evidence.

## Evidence

- RED:
  `artifacts/slices/067-cross-runtime-observability-and-regression-gate/red.txt`
- Focused green:
  `artifacts/slices/067-cross-runtime-observability-and-regression-gate/focused.txt`
- Backend gates:
  `artifacts/slices/067-cross-runtime-observability-and-regression-gate/backend-gates.txt`
  (`27 passed, 1 warning`)
- Browser UAT:
  `artifacts/slices/067-cross-runtime-observability-and-regression-gate/uat.md`
  and `artifacts/slices/067-cross-runtime-observability-and-regression-gate/screenshots/browser-uat-cross-runtime-observability.png`
- Slice E frontend canvas runtime v2 audit closure:
  RED `artifacts/slices/067-cross-runtime-observability-and-regression-gate/slice-e-frontend-canvas-debug-runtime-v2/red.txt`;
  focused unit `artifacts/slices/067-cross-runtime-observability-and-regression-gate/slice-e-frontend-canvas-debug-runtime-v2/focused.txt`;
  rem gate `artifacts/slices/067-cross-runtime-observability-and-regression-gate/slice-e-frontend-canvas-debug-runtime-v2/rem.txt`;
  full frontend unit `artifacts/slices/067-cross-runtime-observability-and-regression-gate/slice-e-frontend-canvas-debug-runtime-v2/frontend-unit.txt`;
  build `artifacts/slices/067-cross-runtime-observability-and-regression-gate/slice-e-frontend-canvas-debug-runtime-v2/build.txt`;
  Browser UAT `artifacts/slices/067-cross-runtime-observability-and-regression-gate/slice-e-frontend-canvas-debug-runtime-v2/uat.md`.

Note: the customer-assistant deterministic router currently exposes one
Chatflow SOP plus non-SOP baggage QA. Same-session routed-task isolation is
covered by the available router path; v1 fallback/no-fake-v2 refs remain covered
by adapter and regression gates from 066/067.
