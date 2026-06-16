# Tasks 066: Customer Assistant Async Chatflow SOP Worker Adapter

## 066.0 Sign-off

- [x] Confirm ChatflowSopWorker v2 use is graph-level only.
- [x] Confirm SOP multi-level router remains the owner of intent/task switching.
- [x] Confirm v1 fallback remains mandatory.
- [x] Confirm missing Chatflow data is reported as data-readiness failure.
- [x] Confirm v2 SOP dispatch is idempotent for the same task/checkpoint.
- [x] Confirm v1 fallback never emits fake v2 refs/events.
- [x] Confirm Chatflow runtime v2 receives router context and does not own route
      state.
- [x] Confirm blocking Chatflow node prompts are preserved as customer drafts.

## 066.1 Runtime Selection

- [x] RED: compatible Chatflow SOP still uses only v1 adapter.
- [x] Add v2 compatibility probe before SOP execution.
- [x] Select Chatflow v2 for compatible graph.
- [x] Deduplicate v2 Chatflow run start by assistant task/binding/request hash.
- [x] Emit explicit fallback reason for unsupported graph.
- [x] Preserve v1 adapter fallback under the same SOP router call contract.

## 066.2 Worker Refs And Events

- [x] Store Chatflow runtime refs in worker/task state.
- [x] Project Chatflow progress summaries into customer-assistant timeline.
- [x] Project blocking node prompt/followup/pendingPrompt into waiting
      recommendation evidence.
- [x] Propagate actor/source/session/task metadata into refs/events where
      supported.
- [x] Propagate SOP router context: `sop_key`, `route_id`, `route_turn_id`,
      `intent_key`, `task_id`, and `session_id`.
- [x] Redact Chatflow event summaries before exposing them in assistant timeline.
- [x] Preserve raw Chatflow refs for debug.

## 066.3 Resume

- [x] RED: waiting Chatflow v2 SOP cannot resume through customer assistant.
- [x] Persist v2 checkpoint metadata.
- [x] Resume through runtime v2.
- [x] Prove duplicate resume for the same checkpoint/input is safe.
- [x] Prove waiting `QUESTION`, `HUMAN_INPUT`, and
      `INFORMATION_COLLECTION` prompts become customer drafts without being
      rewritten.

## 066.4 Compatibility

- [x] Prove existing v1 SOP worker path still works.
- [x] Prove unsupported graph fallback does not emit fake v2 live events.
- [x] Prove worker timeout/cancel maps to Chatflow v2 cancellation or
      cancellation-unsupported evidence.
- [x] Prove SOP router can switch intent A -> intent B -> resume intent A with
      separate task context and checkpoints.
- [x] Prove one routed task can use Chatflow v2 while another routed task falls
      back to v1 in the same session.

## 066.5 Browser UAT

- [x] Verify compatible SOP shows live progress.
- [x] Verify multi-intent SOP routing still switches and resumes tasks
      correctly.
- [x] Verify waiting Chatflow node prompt appears in customer draft and operator
      next-step recommendation.
- [x] Verify unsupported SOP shows fallback reason.

## Evidence

- RED: `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/red.txt`
- Additional RED for timeout/cancel evidence:
  `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/red-timeout.txt`
- Timeout/cancel focused green:
  `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/timeout.txt`
- Router coexistence focused green:
  `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/route-compat.txt`
- Backend gates:
  `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/backend-gates.txt`
  (`19 passed, 1 warning`)
- Browser UAT:
  `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/uat.md`
  and `artifacts/slices/066-customer-assistant-async-chatflow-sop-worker-adapter/screenshots/browser-uat-chatflow-sop-v2.png`

Note: customer-assistant deterministic routing currently exposes one Chatflow SOP
(`refund_ticket`) plus non-SOP baggage QA. The same-session coexistence proof
covers v2 SOP wait/resume while another routed task completes; unsupported
Chatflow fallback is proven separately at adapter level and in the backend gate.
