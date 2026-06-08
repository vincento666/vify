# Tasks 040: Runtime Fallback E2E And Lab Acceptance

## 040.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 036-039.

## 040.1 Backend E2E scenario matrix

- [x] RED: E2E matrix fails for missing route layers/evidence.
- [x] Add scenario fixtures for handoff, FAQ exact, FAQ semantic, SOP,
  RAG, Agent fallback, clarification, and escalation.
- [x] Prove all scenarios through runtime-lab message API.
- [x] Save evidence under
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.1/`.
- [x] Include 040.1 evidence in the final 040 acceptance commit.

## 040.2 Frontend lab evidence hardening

- [x] RED: real UAT exposed low-confidence RAG blocking Agent fallback and
  default Fake Agent lacking handoff recommendation.
- [x] Extend runtime evidence only as needed; no frontend/rem change was needed.
- [x] Run targeted backend tests for low RAG -> Agent and Fake Agent handoff.
- [x] Save evidence under
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.2/`.
- [x] Include 040.2 hardening in the final 040 acceptance commit.

## 040.3 Browser UAT final gate

- [x] RED: browser UAT fails until representative mixed flows pass.
- [x] Run browser UAT for active SOP + FAQ, explicit handoff, semantic FAQ,
  RAG, Agent clarification, and escalation.
- [x] Save screenshots/transcripts under
  `artifacts/slices/040-runtime-fallback-e2e-lab-acceptance/040.3/`.
- [x] Run full backend and frontend gates or document unrelated failures.
- [x] Include 040.3 UAT evidence in the final 040 acceptance commit.

## 040 Completion Gate

- [x] Full route stack E2E matrix passes.
- [x] Browser UAT passes.
- [x] Existing SOP switch/resume and non-interruptible rejection remain valid.
- [x] Final capability summary is updated in `spec.md`.
