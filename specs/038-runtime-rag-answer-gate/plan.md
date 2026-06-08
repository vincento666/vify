# Plan 038: Runtime RAG Answer Gate

## Architecture

```text
RuntimeLabService
  -> handoff / FAQ / SOP arbitration
  -> RagAnswerGate
       -> KnowledgeFacade.search_context(mode=auto|hybrid|semantic)
       -> RagAnswerGeneratorPort
  -> policy decision ANSWER_RAG | CLARIFY | HANDOFF_TO_HUMAN
```

RAG proposal:

```text
{
  action: ANSWER_RAG,
  answer,
  confidence,
  citations,
  retrievalEvidence,
  generationEvidence,
  mutatesSopState: false
}
```

## TDD Strategy

RED tests:

- `ANSWER_RAG` unsupported;
- no-active long-tail query cannot answer with citations;
- active SOP RAG answer mutates task state;
- low-confidence RAG does not clarify/handoff safely;
- classifier input includes only finite SOP/resume/continue candidates.

GREEN:

- add route action;
- add RAG gate and generator port;
- use fake generator in tests;
- emit evidence and events.

## Evidence

Use:

```text
artifacts/slices/038-runtime-rag-answer-gate/
  038.1/
  038.2/
  038.3/
```

Live LLM generation remains opt-in.

Completed evidence:

- `038.1/red.txt`, `038.1/unit.txt`
- `038.2/red.txt`, `038.2/unit-integration.txt`
- `038.3/red.txt`
- `038.3/red-browser-confidence.txt`
- `038.3/red-sop-low-rag.txt`
- `038.3/unit-integration-after-browser-fix.txt`
- `038.3/unit-integration-after-sop-rag-order.txt`
- `038.3/final-targeted.txt`: `40 passed, 1 warning`
- `038.3/browser-uat-result.json`: Swagger Browser UAT PASS
- `038.3/screenshots/browser-uat-rag.png`
- `038.3/full-backend.txt`: `465 passed, 8 skipped, 15 failed`

## SDD Gate

038 started only after 033, 036, and 037 route contracts passed. It consumes
035 retrieval through runtime ports and must not add RAG document snippets to
SOP/task classifier candidates.

Each slice must update `spec.md`, `plan.md`, `tasks.md`, and the corresponding
artifact directory before sign-off. 038 is complete because RAG answers carry
citations/evidence, low-confidence cases clarify or handoff by policy, and
answer-only paths are proven not to mutate active SOP state.
