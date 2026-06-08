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
