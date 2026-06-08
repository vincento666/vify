# Tasks 037: Runtime FAQ Embedding Answer Gate

## 037.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 035 and 036.

## 037.1 Semantic FAQ proposal contract

- [x] RED: runtime-lab has no semantic FAQ proposal gate.
- [x] Add `FaqSemanticAnswerGate` using KnowledgeFacade retrieval mode `faq`.
- [x] Normalize retrieval results into confidence, margin, and evidence.
- [x] Save evidence under
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.1/`.
- [x] Commit 037.1 only. Folded into the 037 completion commit after all
  sub-slice gates passed.

## 037.2 Semantic FAQ policy thresholds

- [x] RED: paraphrased FAQ does not answer with high-confidence semantic hit.
- [x] RED: low-margin semantic FAQ does not clarify safely.
- [x] Add answer/clarify/fallthrough thresholds.
- [x] Include rerank evidence when available.
- [x] Save evidence under
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.2/`.
- [x] Commit 037.2 only. Folded into the 037 completion commit after all
  sub-slice gates passed.

## 037.3 Active-SOP semantic FAQ safety

- [x] RED: semantic FAQ inside active SOP mutates task state.
- [x] RED: FAQ candidates leak into constrained SOP classifier input.
- [x] Preserve active/suspended task state for semantic FAQ answers.
- [x] Ensure classifier input remains finite SOP/resume/continue only.
- [x] Run 036 and SOP regression gates.
- [x] Save evidence under
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/`.
- [x] Commit 037.3 only. Folded into the 037 completion commit after all
  sub-slice gates passed.

## 037 Completion Gate

- [x] Runtime-lab API E2E proves semantic FAQ answer and low-margin clarify.
- [x] Browser-control UAT proves semantic FAQ answer and low-margin clarify.
- [x] Existing exact FAQ, handoff, SOP switch/resume gates pass.
- [x] Full backend pytest passes or unrelated failures are documented.

## Evidence

- 037.1 RED:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.1/red.txt`
- 037.1 unit:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.1/unit.txt`
- 037.2 RED:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.2/red.txt`
- 037.2 unit/integration:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.2/unit-integration.txt`
- 037.3 RED:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/red.txt`
- 037.3 unit/integration:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/unit-integration.txt`
- Final targeted API E2E/regression:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/final-targeted.txt`
- Browser-control UAT:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/uat.md`
- Browser raw evidence:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/browser-uat-result.json`
- Browser screenshot:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/screenshots/browser-uat-semantic-faq.png`
- Full backend attempt:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/full-backend.txt`
