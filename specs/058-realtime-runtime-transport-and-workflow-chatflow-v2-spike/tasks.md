# Tasks 058: Realtime Runtime Transport And Workflow/Chatflow V2 Spike

## 058.0 Sign-off

- [x] Confirm 058 starts after 053 design and 056 worker hardening.
- [x] Confirm the first runtime v2 spike is Chatflow-first, not generic
      Workflow/Chatflow replacement.
- [x] Confirm SSE remains default unless bidirectional control is needed.
- [x] Confirm WebSocket/Redis are justified by product/runtime evidence, not
      added preemptively.
- [x] Confirm database persistence strategy is aligned with the MySQL 8
      migration path or explicitly marked as temporary.
- [x] Confirm legacy Chatflow SSE remains completion-time replay compatibility,
      while v2 live events use a new endpoint or explicit v2 mode.

## 058.1 ADR

- [x] Write ADR comparing SSE, streaming POST, WebSocket, and Redis/pubsub.
- [x] Decide MVP transport.
- [x] Document database persistence strategy and Chatflow seed/import path.
- [x] Document runtime event sequence strategy, including MySQL 8 production
      path or single-process spike limitation.

## 058.2 Runtime V2 Spike

- [x] RED: run-v2 contract test fails because durable run/event refs do not
      exist.
- [x] Add Chatflow v2 path for `START -> MESSAGE -> END`.
- [x] Add Chatflow v2 path for `START -> QUESTION -> resume -> END`.
- [x] Emit durable L1 node events.
- [x] Prove `workflow_run_started` or `workflow_node_started` is observable
      before terminal result is available.
- [x] Expose status, result, and event stream refs.
- [x] Verify run/event/checkpoint data survives process restart or document why
      this slice is still a persistence prototype.

## 058.3 Compatibility Wrapper

- [x] Prove existing synchronous endpoint response remains compatible.
- [x] Prove legacy Chatflow SSE replay behavior remains compatible and separate
      from v2 live event streaming.
- [x] Add regression tests for old API consumers.

## 058.4 Browser UAT

- [x] Verify customer assistant still works.
- [x] Verify v2 spike emits visible progress events while the run is still
      active.
- [x] Save screenshots and UAT notes.
