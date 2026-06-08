# Plan 037: Runtime FAQ Embedding Answer Gate

## Architecture

```text
RuntimeLabService
  -> HandoffPolicy
  -> FaqExactAnswerGate
  -> FaqSemanticAnswerGate
       -> KnowledgeFacade.search_context(mode=faq, rerank=?, topK=?, threshold=?)
  -> SOP arbitration
```

The semantic FAQ gate consumes 035 retrieval outputs and normalizes them into a
policy proposal:

```text
ANSWER_FAQ proposal {
  answer,
  confidence,
  margin,
  retrievalMode: faq,
  rerankUsed,
  topCandidates,
  mutatesSopState: false
}
```

## TDD Strategy

RED tests:

- paraphrased FAQ currently falls through to SOP/clarify;
- low-margin semantic FAQ currently lacks safe clarification;
- active SOP semantic FAQ currently risks slot consumption;
- classifier input must not contain FAQ/RAG snippets.

Implementation is adapter-level: call existing 035 retrieval mode and apply
runtime policy thresholds.

## Evidence

Use:

```text
artifacts/slices/037-runtime-faq-embedding-answer-gate/
  037.1/
  037.2/
  037.3/
```

No live embedding provider is required for CI. Fake/local vector evidence is
acceptable if the adapter contract is the same.
