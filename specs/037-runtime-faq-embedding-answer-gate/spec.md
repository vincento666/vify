# Spec 037: Runtime FAQ Embedding Answer Gate

## Goal

Connect semantic FAQ recall, embedding scores, and rerank evidence from 035 into
runtime-lab candidate recall.

037 handles paraphrased FAQ questions that do not match exact/keyword rules by
creating `ANSWER_FAQ` candidates with semantic evidence. Final FAQ-vs-SOP
selection is made by central constrained LLM arbitration plus PolicyGate.

## Dependency

Required:

- 033 handoff foundation complete;
- 035 retrieval productization complete, including FAQ vector recall, retrieval
  modes, vector-store adapter, and rerank contracts;
- 036 exact FAQ answer gate complete.

## Scope

In scope:

- semantic FAQ candidate generation using retrieval mode `faq` or equivalent
  structured FAQ vector recall;
- top-k FAQ evidence with score, margin, retrieval mode, rerank state, and
  source metadata;
- policy thresholds for candidate inclusion and evidence quality;
- active-SOP safe semantic FAQ answer;
- explicit guarantee that FAQ candidates enter the unified classifier as
  `ANSWER_FAQ`, not as SOP intent candidates.

Out of scope:

- document RAG generation;
- fallback Agent;
- training/reranker quality tuning beyond configured thresholds;
- changing 035 retrieval internals.

## Routing Position

```text
033 handoff hard stops
  -> unified hybrid candidate recall
       exact FAQ candidates
       037 semantic FAQ candidates
       SOP/resume/RAG/Agent candidates
  -> central constrained LLM arbitration
  -> PolicyGate
  -> typed executor
```

If active SOP exists, 037 must be stricter:

- answer only if the utterance is clearly a question and semantic margin is
  high;
- otherwise ask clarification or continue SOP as policy decides.

## Acceptance Criteria

- paraphrased FAQ query creates an `ANSWER_FAQ` candidate with semantic
  evidence;
- low score or low margin does not enter the candidate pool or enters as
  low-confidence evidence according to policy;
- semantic FAQ answer preserves active SOP state;
- semantic FAQ result enters central classifier input as `ANSWER_FAQ`, never as
  `SOP_INTENT`;
- rerank evidence is included when rerank is enabled;
- 036 exact FAQ behavior remains stable.

## Completion Capability

After 037, runtime-lab can answer structured FAQ questions even when users do
not use the configured FAQ wording, while preserving SOP rigor and producing
auditable retrieval evidence.

## Unified Arbitration Refactor Gate

Status: completed on 2026-06-09.

The previous 037 evidence proves the old semantic FAQ answer gate. The current
architecture requires semantic FAQ to become typed candidate evidence for
central arbitration.

R1 evidence:

- RED/shared conflict regression:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.R1/red-shared-faq-sop-conflict.txt`
- Integration:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.R1/integration.txt`

## Specification Sign-off

Status: complete.

Numbering was rechecked on 2026-06-09. 037 follows 036 and depends on 035's FAQ
embedding/retrieval contracts; it is the runtime routing consumer, not a
knowledge-module rebuild.

## Completion Evidence

Completed on 2026-06-09 with the following gates:

- RED:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.1/red.txt`,
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.2/red.txt`,
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/red.txt`
- Unit/integration:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.1/unit.txt`,
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.2/unit-integration.txt`,
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/unit-integration.txt`
- Runtime-lab API E2E and 033/036/SOP regression:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/final-targeted.txt`
  (`31 passed`)
- Browser UAT through Swagger UI:
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/uat.md`,
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/browser-uat-result.json`,
  `artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/screenshots/browser-uat-semantic-faq.png`

Full backend pytest was attempted and saved to
`artifacts/slices/037-runtime-faq-embedding-answer-gate/037.3/full-backend.txt`.
It produced `456 passed, 8 skipped, 15 failed`; the remaining failures match
the documented non-037 residue from runtime-lab chatflow-adapter host resolution
and workflow knowledge-facade stub drift.
