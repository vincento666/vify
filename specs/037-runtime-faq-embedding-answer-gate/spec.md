# Spec 037: Runtime FAQ Embedding Answer Gate

## Goal

Connect semantic FAQ recall, embedding scores, and rerank evidence from 035 into
runtime-lab policy.

037 handles paraphrased FAQ questions that do not match exact/keyword rules but
can be answered from structured FAQ entries with high semantic confidence.

## Dependency

Required:

- 033 handoff foundation complete;
- 035 retrieval productization complete, including FAQ vector recall, retrieval
  modes, vector-store adapter, and rerank contracts;
- 036 exact FAQ answer gate complete.

## Scope

In scope:

- semantic FAQ proposal gate using retrieval mode `faq` or equivalent
  structured FAQ vector recall;
- top-k FAQ evidence with score, margin, retrieval mode, rerank state, and
  source metadata;
- policy thresholds for answer, clarify, or continue to SOP arbitration;
- active-SOP safe semantic FAQ answer;
- explicit guarantee that FAQ candidates do not become SOP intent candidates.

Out of scope:

- document RAG generation;
- fallback Agent;
- training/reranker quality tuning beyond configured thresholds;
- changing 035 retrieval internals.

## Routing Position

```text
033 handoff hard stops
  -> 036 exact FAQ
  -> 037 semantic FAQ
  -> SOP/resume arbitration
  -> RAG/Agent fallback
```

If active SOP exists, 037 must be stricter:

- answer only if the utterance is clearly a question and semantic margin is
  high;
- otherwise ask clarification or continue SOP as policy decides.

## Acceptance Criteria

- paraphrased FAQ query returns `ANSWER_FAQ` with semantic evidence;
- low score or low margin does not answer;
- semantic FAQ answer preserves active SOP state;
- semantic FAQ result never enters constrained SOP classifier candidate set;
- rerank evidence is included when rerank is enabled;
- 036 exact FAQ behavior remains stable.

## Completion Capability

After 037, runtime-lab can answer structured FAQ questions even when users do
not use the configured FAQ wording, while preserving SOP rigor and producing
auditable retrieval evidence.

## Specification Sign-off

Status: ready for implementation.

Numbering was rechecked on 2026-06-09. 037 follows 036 and depends on 035's FAQ
embedding/retrieval contracts; it is the runtime routing consumer, not a
knowledge-module rebuild.
