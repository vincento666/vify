# Tasks 070: Realtime Control And Scale-out Transport

## 070.0 Sign-off

- [x] Confirm current product/runtime evidence does not require more than SSE
      plus durable polling.
- [x] Confirm durable event store remains source of truth.
- [x] Confirm connection loss does not delete runs.
- [x] Confirm realtime connections are authorized by run/session/tenant scope.
- [x] Confirm transport decision does not change runtime semantics.
- [x] Confirm SOP multi-level router compatibility gates remain green before
      070 completion.

## 070.1 ADR

- [x] Compare SSE, streaming POST, WebSocket, Redis/pubsub, and DB polling.
- [x] Decide whether implementation is justified.
- [x] Document delivery semantics, heartbeat, reconnect, and backpressure.
- [x] Document auth and tenant/session scoping.
- [x] If not justified, record no-go and stop.

## 070.2 Narrow Control Spike

- [x] N/A: no justified realtime control scenario was accepted.
- [x] N/A: no WebSocket/control implementation added.
- [x] N/A: existing SSE/session/run APIs keep current auth dependencies.
- [x] Existing run/status/event/result refs preserved by backend gates.

## 070.3 Reconnect And Fanout

- [x] Prove reconnect by `afterSequence`.
- [x] Prove heartbeat behavior.
- [x] Prove max-connection/backpressure behavior or document MVP bounds.
- [x] N/A: pub/sub not used; ADR documents durable replay requirement for any
      future broker miss.

## 070.4 Browser UAT

- [x] N/A: realtime control behavior was no-go for this MVP.
- [x] Verify reconnect behavior.
- [x] Verify SOP router can still call Chatflow SOP, switch intents, resume a
      suspended task, and fall back to v1 when needed.
- [x] Save screenshots and notes.

## 070 Evidence

- RED: `artifacts/slices/070-realtime-control-and-scale-out-transport/red.txt`
- Unit: `artifacts/slices/070-realtime-control-and-scale-out-transport/unit.txt`
- Backend gate: `artifacts/slices/070-realtime-control-and-scale-out-transport/backend-gates.txt`
- E2E: `artifacts/slices/070-realtime-control-and-scale-out-transport/e2e.txt`
- Browser UAT: `artifacts/slices/070-realtime-control-and-scale-out-transport/uat.md`
- ADR: `docs/adr/0004-realtime-control-scaleout-transport.md`
