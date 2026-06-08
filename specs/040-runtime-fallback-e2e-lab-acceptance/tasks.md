# Tasks 040: Runtime Fallback E2E And Lab Acceptance

## 040.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 036-039.

## 040.1 Backend E2E scenario matrix

- [ ] RED: E2E matrix fails for missing route layers/evidence.
- [ ] Add scenario fixtures for handoff, FAQ exact, FAQ semantic, SOP,
  RAG, Agent fallback, clarification, and escalation.
- [ ] Prove all scenarios through runtime-lab message API.
- [ ] Save evidence under
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.1/`.
- [ ] Commit 040.1 only.

## 040.2 Frontend lab evidence hardening

- [ ] RED: frontend cannot show fallback source/evidence where required.
- [ ] Extend 034 lab inspector only as needed for FAQ/RAG/Agent/handoff
  evidence.
- [ ] Run targeted frontend tests and REM gate.
- [ ] Save evidence under
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.2/`.
- [ ] Commit 040.2 only.

## 040.3 Browser UAT final gate

- [ ] RED: browser UAT fails until representative mixed flows pass.
- [ ] Run browser UAT for active SOP + FAQ, explicit handoff, semantic FAQ,
  RAG, Agent clarification, and escalation.
- [ ] Save screenshots/transcripts under
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.3/`.
- [ ] Run full backend and frontend gates or document unrelated failures.
- [ ] Commit 040.3 only.

## 040 Completion Gate

- [ ] Full route stack E2E matrix passes.
- [ ] Browser UAT passes.
- [ ] Existing SOP switch/resume and non-interruptible rejection remain valid.
- [ ] Final capability summary is updated in `spec.md`.
