# Tasks 033: Runtime Handoff Foundation

## 033.0 Spec refinement

- [x] Keep original fallback-policy intent.
- [x] Refine 033 into shared handoff/control-plane foundation.
- [x] Move FAQ exact, FAQ embedding, RAG, Agent fallback, and final browser
  acceptance into later specs.
- [x] Document current baseline and missing runtime-lab handoff behavior.

## 033.1 Handoff action contract

- [x] RED: classifier/action validation rejects `HANDOFF_TO_HUMAN`.
- [x] RED: policy gate cannot return `HANDOFF_TO_HUMAN`.
- [x] RED: runtime-lab payload lacks normalized handoff evidence.
- [x] Add `HANDOFF_TO_HUMAN` to route actions and finite classifier actions.
- [x] Add `HANDOFF_TO_HUMAN` candidate type and serialization.
- [x] Add policy-gate mapping from candidate/classifier result to route
  decision.
- [x] Save RED/GREEN evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.1/`.
- [x] Defer commit until full 033 high-spec gate audit passes.

## 033.2 Explicit handoff trigger templates

- [x] RED: explicit user request for human support does not trigger handoff.
- [x] RED: complaint/compliance/safety/unsupported phrases do not trigger
  handoff.
- [x] Add explicit handoff signal detector with stable reason codes.
- [x] Ensure hard-stop triggers run before FAQ/SOP/RAG/Agent layers.
- [x] Ensure active/suspended tasks are not mutated by trigger detection alone.
- [x] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.2/`.
- [x] Defer commit until full 033 high-spec gate audit passes.

## 033.3 Runtime handoff event and context snapshot

- [x] RED: runtime-lab does not emit `HANDOFF_DECIDED` and
  `HANDOFF_REQUESTED` events.
- [x] RED: context snapshot lacks active task, suspended tasks, business refs,
  route evidence, and recent transcript.
- [x] Add handoff runtime adapter over existing handoff service or a fake test
  adapter.
- [x] Preserve active/suspended task state according to explicit policy.
- [x] Return a user-facing handoff reply without leaking internal evidence.
- [x] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.3/`.
- [x] Defer commit until full 033 high-spec gate audit passes.

## 033.4 Handoff policy regression gate

- [x] RED: E2E fails until explicit handoff works through
  `/api/v1/runtime-lab/sessions/{id}/messages`.
- [x] Prove existing SOP start/switch/resume/completion tests still pass.
- [x] Prove non-interruptible SOP switch rejection still passes.
- [x] Prove handoff does not consume active SOP slots.
- [x] Run targeted runtime-lab and handoff tests.
- [x] Run full backend pytest or document unrelated failures.
- [x] Save final evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.4/`.
- [x] Commit 033 complete slice after RED/unit/integration/contract/e2e/browser
  UAT evidence is verified.

## Future specs

- [ ] 036 Runtime FAQ exact answer gate.
- [ ] 037 Runtime semantic FAQ embedding gate.
- [ ] 038 Runtime RAG answer gate.
- [ ] 039 Runtime controlled Agent fallback and escalation.
- [ ] 040 Runtime fallback E2E and lab acceptance.
