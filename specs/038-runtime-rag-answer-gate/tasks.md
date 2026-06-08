# Tasks 038: Runtime RAG Answer Gate

## 038.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 036/037.

## 038.1 RAG action and generator port

- [x] RED: `ANSWER_RAG` is unsupported as route action.
- [x] RED: RAG generator port does not exist.
- [x] Add `ANSWER_RAG` route action and payload formatter.
- [x] Add `RagAnswerGeneratorPort` with fake deterministic implementation.
- [x] Save evidence under
  `artifacts/slices/038-runtime-rag-answer-gate/038.1/`.
- [x] Commit as part of 038 gated slice.

## 038.2 No-active RAG answer gate

- [x] RED: long-tail document query cannot return cited RAG answer.
- [x] Add retrieval proposal from KnowledgeFacade document/chunk results.
- [x] Add answer generation and citation evidence.
- [x] Add low-confidence clarify/handoff policy.
- [x] Save evidence under
  `artifacts/slices/038-runtime-rag-answer-gate/038.2/`.
- [x] Commit as part of 038 gated slice.

## 038.3 Active-SOP RAG safety

- [x] RED: active SOP RAG question mutates task state.
- [x] RED: RAG snippets leak into SOP classifier input.
- [x] Preserve task state for accepted RAG answers.
- [x] Clarify ambiguous active SOP RAG-vs-slot input.
- [x] Run FAQ/SOP/handoff regressions.
- [x] Save evidence under
  `artifacts/slices/038-runtime-rag-answer-gate/038.3/`.
- [x] Commit as part of 038 gated slice.

## 038 Completion Gate

- [x] Runtime-lab API E2E proves no-active and active-SOP RAG behavior.
- [x] Browser UAT proves Swagger-visible no-active RAG, SOP start, and
  active-SOP RAG state preservation.
- [x] Existing 033/036/037 gates pass.
- [x] Full backend pytest passes or unrelated failures are documented.
