# Tasks 036: Runtime FAQ Exact Answer Gate

## 036.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 035.
- [x] Define TDD/SDD gates and non-goals.

## 036.1 FAQ action and exact proposal contract

- [ ] RED: `ANSWER_FAQ` is not serializable as a runtime route action.
- [ ] RED: FAQ exact proposal contract does not exist.
- [ ] Add `ANSWER_FAQ` route action and formatter payload.
- [ ] Add `FaqExactAnswerGate` proposal DTO and evidence shape.
- [ ] Save evidence under
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.1/`.
- [ ] Commit 036.1 only.

## 036.2 No-active FAQ answer gate

- [ ] RED: exact/high-confidence FAQ query does not answer before SOP
  arbitration.
- [ ] RED: explicit handoff phrase mixed with FAQ does not handoff first.
- [ ] Implement exact/normalized/keyword FAQ scoring with threshold and margin.
- [ ] Ensure FAQ hits are not passed to constrained SOP classifier.
- [ ] Emit `FAQ_ANSWERED` or equivalent route event.
- [ ] Save evidence under
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/`.
- [ ] Commit 036.2 only.

## 036.3 Active-SOP FAQ safety

- [ ] RED: active SOP FAQ question mutates checkpoint/business refs.
- [ ] RED: ambiguous active-SOP input does not clarify.
- [ ] Preserve active/suspended task state for accepted FAQ answers.
- [ ] Add ambiguity policy for FAQ-vs-slot conflict.
- [ ] Run runtime-lab SOP regression gates.
- [ ] Save evidence under
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/`.
- [ ] Commit 036.3 only.

## 036 Completion Gate

- [ ] Targeted unit/integration tests pass.
- [ ] Runtime-lab API E2E proves FAQ answer before SOP and active-SOP FAQ
  safety.
- [ ] Existing 033 handoff and 034 SOP lab gates remain valid.
- [ ] Full backend pytest passes or unrelated failures are documented.
