# Tasks 048: Customer Assistant Live L1 Events SSE

## 048.0 Spec Sign-off

- [x] Confirm 048 uses independent SSE, not WebSocket.
- [x] Confirm SSE reads from persisted `customer_assistant_event`.
- [x] Confirm 048 must prove real execution-time events, not replay after turn
      completion.
- [x] Confirm internal Chatflow/SOP node-level events remain summarized payloads
      in 048.
- [x] Confirm frontend primary UI is task/stage progress, with timeline
      collapsed as evidence.
- [x] Save sign-off evidence under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.0/`.

## 048.1 Backend SSE Endpoint

- [x] RED: contract test fails for missing
      `GET /api/v1/customer-assistant/sessions/{sessionId}/events/stream`.
- [x] Add SSE endpoint with `afterSequence` query parameter.
- [x] Serialize existing event rows as SSE frames with `id`, `event`, and JSON
      `data`.
- [x] Support resume from `afterSequence`.
- [x] Add heartbeat behavior for idle streams.
- [x] Preserve existing list-events endpoint behavior.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.1/`.

## 048.2 Runtime Timing And L1 Event Normalization

- [x] RED: runtime test fails because recommendation start/complete and timing
      payloads are missing.
- [x] Emit `recommendation_started` before aggregation.
- [x] Emit `recommendation_completed` after aggregation.
- [x] Add `startedAt`, `completedAt`, and `elapsedMs` where phase boundaries
      are available.
- [x] Ensure worker start/result events include enough task and span metadata
      for frontend progress.
- [x] Add run failure event on controlled runtime exceptions.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.2/`.

## 048.3 Execution-Time Streaming Proof

- [x] RED: concurrency test proves current behavior only exposes events after
      the turn completes. Note: pre-SSE red is captured in 048.1; after 048.1
      the concurrency proof was already green. See 048.3/red-note.md.
- [x] Add a test-only slow worker or blocking scheduler fixture.
- [x] Open SSE stream before posting a turn.
- [x] Start `POST /turns` concurrently.
- [x] Assert progress events arrive on SSE while `POST /turns` is still
      pending.
- [x] Assert final events arrive after the worker is released.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.3/`.

## 048.4 Frontend SSE Client

- [x] RED: frontend test fails because no event stream client exists.
- [x] Add customer-assistant SSE client with `afterSequence` support.
- [x] Parse event frames into existing `CustomerAssistantEvent` shape.
- [x] Track last seen sequence.
- [x] Expose start/stop lifecycle for the panel.
- [x] Surface stream errors without clearing current session state.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.4/`.

## 048.5 Live Progress Panel Integration

- [x] RED: component/view-model tests fail because stage checklist does not
      update from events.
- [x] Ensure session is created before the first turn stream is opened.
- [x] Merge incoming events into runtime state while turn request is pending.
- [x] Show stage checklist:
      `Recognizing tasks`, `Running workers`, `Generating recommendation`,
      `Ready for operator`.
- [x] Update task rows from live events and final reconciliation refresh.
- [x] Keep Event Timeline collapsed by default under the operator side.
- [x] Run rem governance if visual files are touched.
- [x] Gates pass and evidence is saved under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.5/`.

## 048.6 Browser UAT And Final Acceptance

- [x] Run focused backend SSE/event tests.
- [x] Run focused frontend customer-assistant tests.
- [x] Run `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`
      if visual files changed.
- [x] Run live backend + Vite UAT on `/customer-assistant`.
- [x] Verify progress appears before the turn result is complete.
- [x] Verify timeline is collapsed by default.
- [x] Verify no WebSocket or Redis/pubsub dependency was added.
- [x] Save screenshots and UAT notes under
      `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.6/`.

## Evidence

- 048.0 sign-off:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.0/signoff.md`
- 048.1 SSE endpoint RED/green:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.1/red.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.1/red-heartbeat.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.1/unit.txt`
- 048.2 timing RED/green:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.2/red.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.2/unit.txt`
- 048.3 execution-time proof:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.3/red-note.md`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.3/unit.txt`
- 048.4 frontend SSE client RED/green:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.4/red.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.4/unit.txt`
- 048.5 progress UI RED/green:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.5/red.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.5/unit.txt`
- 048.6 final gates/UAT:
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.6/backend.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.6/frontend.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.6/rem.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.6/e2e.txt`,
  `artifacts/slices/048-customer-assistant-live-l1-events-sse/048.6/uat.md`
