# Tasks 038: Runtime RAG Answer Gate

## 038.0 Spec creation

- [x] Create `spec.md`, `plan.md`, and `tasks.md`.
- [x] Record dependency on 033 and 036/037.

## 038.1 RAG action and generator port

- [ ] RED: `ANSWER_RAG` is unsupported as route action.
- [ ] RED: RAG generator port does not exist.
- [ ] Add `ANSWER_RAG` route action and payload formatter.
- [ ] Add `RagAnswerGeneratorPort` with fake deterministic implementation.
- [ ] Save evidence under
  `artifacts/slices/038-runtime-rag-answer-gate/038.1/`.
- [ ] Commit 038.1 only.

## 038.2 No-active RAG answer gate

- [ ] RED: long-tail document query cannot return cited RAG answer.
- [ ] Add retrieval proposal from KnowledgeFacade document/chunk results.
- [ ] Add answer generation and citation evidence.
- [ ] Add low-confidence clarify/handoff policy.
- [ ] Save evidence under
  `artifacts/slices/038-runtime-rag-answer-gate/038.2/`.
- [ ] Commit 038.2 only.

## 038.3 Active-SOP RAG safety

- [ ] RED: active SOP RAG question mutates task state.
- [ ] RED: RAG snippets leak into SOP classifier input.
- [ ] Preserve task state for accepted RAG answers.
- [ ] Clarify ambiguous active SOP RAG-vs-slot input.
- [ ] Run FAQ/SOP/handoff regressions.
- [ ] Save evidence under
  `artifacts/slices/038-runtime-rag-answer-gate/038.3/`.
- [ ] Commit 038.3 only.

## 038 Completion Gate

- [ ] Runtime-lab API E2E proves no-active and active-SOP RAG behavior.
- [ ] Existing 033/036/037 gates pass.
- [ ] Full backend pytest passes or unrelated failures are documented.
