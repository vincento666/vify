# Spec 067: Cross-runtime Observability And Regression Gate

## Goal

Create a regression and observability gate across Customer Assistant worker
runtime, Hify Chatflow runtime v2, and Hify Workflow runtime v2.

This spec prevents the product from becoming harder to understand as more async
runtime layers are introduced.

## Dependency

067 depends on:

- 061 customer-assistant async worker orchestration;
- 063 Hify Chatflow runtime v2 facade;
- 065 Hify Workflow runtime v2 facade if Workflow v2 is enabled;
- 066 async ChatflowSopWorker adapter if SOP worker v2 is enabled.

## Product Boundary

In scope:

- event summary mapping across assistant, worker, Chatflow, and Workflow runs;
- operator panel evidence for task/worker/runtime progress;
- Workflow/Chatflow canvas debug evidence for node status, running animation,
  completion, waiting, and failure states;
- debug links from customer-assistant task to worker/runtime refs;
- regression gates for old sync APIs and v2 live events;
- regression gates for the existing SOP multi-level router calling Chatflow SOP
  workers through v2-compatible refs or v1 fallback;
- UAT scripts for customer/operator paths.

Out of scope:

- new runtime semantics;
- new node coverage;
- ReAct standardization;
- WebSocket/Redis.

## Hard Constraints

- Timeline must distinguish event source: assistant, worker, Chatflow, Workflow.
- Canvas node state, running animation, completion state, and debug panel rows
  must be projections of runtime v2 node status/events.
- Missing evidence must show warnings, not empty recommendation shells.
- Old API compatibility regressions block completion.
- V2 live events must not be confused with legacy replay events.
- SOP multi-level routing regressions block completion: intent switching,
  task suspend/resume, v1 fallback, and v2-compatible Chatflow SOP calls must
  remain compatible.
- Every cross-runtime summary event must carry enough correlation refs to trace
  the chain: assistant run, task, worker run, runtime run, and source event.
- Timeline entries must label whether they are live events, replayed events, or
  compatibility summaries.
- Observability must include failure/timeout/cancel/fallback states, not only
  happy-path progress.
- Observability must show waiting/blocking reason and the exact node prompt used
  for customer draft when a worker waits for input.
- A node failure must stop the debug run and surface the failed node, error
  message, and terminal run status in the debug panel.
- Sensitive payloads, credentials, raw prompts, and raw provider outputs must be
  redacted before display or artifact export.

## Acceptance Criteria

- Operator panel can show task, worker, and runtime progress coherently.
- Workflow/Chatflow canvas debug run shows live node progress from runtime v2
  events, not completion-time replay.
- Debug panel updates node status in real time and stops on error.
- Waiting Chatflow worker recommendations preserve node prompts/follow-ups in
  customer drafts.
- Debug refs are reachable from task/runtime evidence.
- Trace/correlation refs allow a failed recommendation to be traced back to the
  worker/runtime/source event that caused it.
- Eval/UAT can distinguish runtime bug, worker failure, and missing seed data.
- Evidence artifacts include latency/status/fallback summaries for regression
  comparison.
- Evidence artifacts include SOP router context and prove routed tasks do not
  leak checkpoint, variable, or result state across intents.
- Legacy sync Workflow/Chatflow and customer-assistant MVP flows remain green.

## MVP Exit

067 is complete when cross-runtime observability is good enough to safely expand
node coverage and ReAct behavior without hiding failures.
