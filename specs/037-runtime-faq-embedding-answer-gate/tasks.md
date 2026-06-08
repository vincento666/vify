# Tasks 037: Runtime FAQ Embedding Answer Gate

## 037.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 035 and 036.

## 037.1 Semantic FAQ proposal contract

- [ ] RED: runtime-lab has no semantic FAQ proposal gate.
- [ ] Add `FaqSemanticAnswerGate` using KnowledgeFacade retrieval mode `faq`.
- [ ] Normalize retrieval results into confidence, margin, and evidence.
- [ ] Save evidence under
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.1/`.
- [ ] Commit 037.1 only.

## 037.2 Semantic FAQ policy thresholds

- [ ] RED: paraphrased FAQ does not answer with high-confidence semantic hit.
- [ ] RED: low-margin semantic FAQ does not clarify safely.
- [ ] Add answer/clarify/fallthrough thresholds.
- [ ] Include rerank evidence when available.
- [ ] Save evidence under
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.2/`.
- [ ] Commit 037.2 only.

## 037.3 Active-SOP semantic FAQ safety

- [ ] RED: semantic FAQ inside active SOP mutates task state.
- [ ] RED: FAQ candidates leak into constrained SOP classifier input.
- [ ] Preserve active/suspended task state for semantic FAQ answers.
- [ ] Ensure classifier input remains finite SOP/resume/continue only.
- [ ] Run 036 and SOP regression gates.
- [ ] Save evidence under
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/`.
- [ ] Commit 037.3 only.

## 037 Completion Gate

- [ ] Runtime-lab API E2E proves semantic FAQ answer and low-margin clarify.
- [ ] Existing exact FAQ, handoff, SOP switch/resume gates pass.
- [ ] Full backend pytest passes or unrelated failures are documented.
