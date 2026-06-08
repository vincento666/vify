# Tasks 036: Runtime FAQ Exact Answer Gate

## 036.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 035.
- [x] Define TDD/SDD gates and non-goals.

## 036.1 FAQ action and exact proposal contract

- [x] RED: `ANSWER_FAQ` is not serializable as a runtime route action.
- [x] RED: FAQ exact proposal contract does not exist.
- [x] Add `ANSWER_FAQ` route action and formatter payload.
- [x] Add `FaqExactAnswerGate` proposal DTO and evidence shape.
- [x] Save evidence under
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.1/`.
- [x] Commit 036.1 only. Folded into the 036 completion commit after all
  sub-slice gates passed.

## 036.2 No-active FAQ answer gate

- [x] RED: exact/high-confidence FAQ query does not answer before SOP
  arbitration.
- [x] RED: explicit handoff phrase mixed with FAQ does not handoff first.
- [x] Implement exact/normalized/keyword FAQ scoring with threshold and margin.
- [x] Ensure FAQ hits are not passed to constrained SOP classifier.
- [x] Emit `FAQ_ANSWERED` or equivalent route event.
- [x] Save evidence under
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/`.
- [x] Commit 036.2 only. Folded into the 036 completion commit after all
  sub-slice gates passed.

## 036.3 Active-SOP FAQ safety

- [x] RED: active SOP FAQ question mutates checkpoint/business refs.
- [x] RED: ambiguous active-SOP input does not clarify.
- [x] Preserve active/suspended task state for accepted FAQ answers.
- [x] Add ambiguity policy for FAQ-vs-slot conflict.
- [x] Run runtime-lab SOP regression gates.
- [x] Save evidence under
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/`.
- [x] Commit 036.3 only. Folded into the 036 completion commit after all
  sub-slice gates passed.

## 036 Completion Gate

- [x] Targeted unit/integration tests pass.
- [x] Runtime-lab API E2E proves FAQ answer before SOP and active-SOP FAQ
  safety.
- [x] Existing 033 handoff and 034 SOP lab gates remain valid.
- [x] Browser-control UAT passes through Swagger UI and records screenshot.
- [x] Full backend pytest passes or unrelated failures are documented.

## Evidence

- 036.1 RED:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.1/red.txt`
- 036.1 unit:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.1/unit.txt`
- 036.2 RED:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/red.txt`
- 036.2 knowledge-gate RED:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/red-knowledge-gate.txt`
- 036.2 unit/integration:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/unit-integration.txt`
- 036.3 RED:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/red.txt`
- 036.3 unit/integration:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/unit-integration.txt`
- Final targeted API E2E/regression:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/final-targeted.txt`
- Browser-control UAT:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/uat.md`
- Browser raw evidence:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/browser-uat-result.json`
- Browser screenshot:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/screenshots/browser-uat-faq.png`
- Full backend attempt:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/full-backend.txt`
