# Tasks 033: Runtime Handoff Foundation

## 033.0 Spec refinement

- [x] Keep original fallback-policy intent.
- [x] Refine 033 into shared handoff/control-plane foundation.
- [x] Move FAQ exact, FAQ embedding, RAG, Agent fallback, and final browser
  acceptance into later specs.
- [x] Document current baseline and missing runtime-lab handoff behavior.

## 033.1 Handoff action contract

- [ ] RED: classifier/action validation rejects `HANDOFF_TO_HUMAN`.
- [ ] RED: policy gate cannot return `HANDOFF_TO_HUMAN`.
- [ ] RED: runtime-lab payload lacks normalized handoff evidence.
- [ ] Add `HANDOFF_TO_HUMAN` to route actions and finite classifier actions.
- [ ] Add `HANDOFF_TO_HUMAN` candidate type and serialization.
- [ ] Add policy-gate mapping from candidate/classifier result to route
  decision.
- [ ] Save RED/GREEN evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.1/`.
- [ ] Commit 033.1 only.

## 033.2 Explicit handoff trigger templates

- [ ] RED: explicit user request for human support does not trigger handoff.
- [ ] RED: complaint/compliance/safety/unsupported phrases do not trigger
  handoff.
- [ ] Add explicit handoff signal detector with stable reason codes.
- [ ] Ensure hard-stop triggers run before FAQ/SOP/RAG/Agent layers.
- [ ] Ensure active/suspended tasks are not mutated by trigger detection alone.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.2/`.
- [ ] Commit 033.2 only.

## 033.3 Runtime handoff event and context snapshot

- [ ] RED: runtime-lab does not emit `HANDOFF_DECIDED` and
  `HANDOFF_REQUESTED` events.
- [ ] RED: context snapshot lacks active task, suspended tasks, business refs,
  route evidence, and recent transcript.
- [ ] Add handoff runtime adapter over existing handoff service or a fake test
  adapter.
- [ ] Preserve active/suspended task state according to explicit policy.
- [ ] Return a user-facing handoff reply without leaking internal evidence.
- [ ] Save evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.3/`.
- [ ] Commit 033.3 only.

## 033.4 Handoff policy regression gate

- [ ] RED: E2E fails until explicit handoff works through
  `/api/v1/runtime-lab/sessions/{id}/messages`.
- [ ] Prove existing SOP start/switch/resume/completion tests still pass.
- [ ] Prove non-interruptible SOP switch rejection still passes.
- [ ] Prove handoff does not consume active SOP slots.
- [ ] Run targeted runtime-lab and handoff tests.
- [ ] Run full backend pytest or document unrelated failures.
- [ ] Save final evidence under
  `artifacts/slices/033-runtime-fallback-policy/033.4/`.
- [ ] Commit 033.4 only.

## Future specs

- [ ] 036 Runtime FAQ exact answer gate.
- [ ] 037 Runtime semantic FAQ embedding gate.
- [ ] 038 Runtime RAG answer gate.
- [ ] 039 Runtime controlled Agent fallback and escalation.
- [ ] 040 Runtime fallback E2E and lab acceptance.
