# Spec 038: Runtime RAG Answer Gate

## Goal

Add controlled document RAG answer candidates to runtime-lab for long-tail
knowledge questions that may compete with SOP, FAQ, and Agent candidates.

RAG provides evidence-backed answers and citations. It must not become an SOP
intent source and must not mutate runtime task state.

## Dependency

Required:

- 033 handoff foundation complete;
- 035 retrieval productization complete;
- 036 exact FAQ and 037 semantic FAQ complete.

## Scope

In scope:

- `ANSWER_RAG` route action;
- document/chunk retrieval candidate generation using 035 retrieval options;
- answer generator port with deterministic fake/local implementation for CI;
- evidence payload: retrieval mode, top chunks, scores, citations, generation
  model/mode, safety result;
- active-SOP safe RAG answer and ambiguity clarification.

Out of scope:

- structured FAQ answering already handled by 036/037;
- fallback Agent;
- autonomous tool calling;
- human console UI.

## Routing Position

```text
033 handoff
  -> unified hybrid candidate recall
       FAQ/SOP/resume candidates
       038 RAG answer candidates
       Agent/handoff/clarify candidates
  -> central constrained LLM arbitration
  -> PolicyGate
  -> typed executor
```

RAG no longer runs as a separate post-SOP answer gate. It contributes typed
`ANSWER_RAG` candidates with citations/evidence. Raw document snippets are not
SOP targets and must not be represented as `SOP_INTENT`.

## Acceptance Criteria

- long-tail document question creates `ANSWER_RAG` candidate with citations;
- low retrieval confidence returns clarification or handoff according to policy;
- active SOP RAG answer preserves task state;
- RAG snippets enter classifier evidence only as `ANSWER_RAG` candidates, never
  as `SOP_INTENT`;
- generation is controlled by a port and can be fake/deterministic in CI;
- RAG answer can recommend but not directly create handoff unless 033 policy
  approves.

## Completion Capability

After 038, runtime-lab can answer long-tail knowledge questions with cited
evidence while keeping SOP routing deterministic and auditable.

## Unified Arbitration Refactor Gate

Status: completed on 2026-06-09.

The previous 038 evidence proves the old post-SOP RAG answer gate. The current
architecture requires RAG to become typed candidate evidence for central
arbitration.

R1 evidence:

- RED:
  `artifacts/slices/038-runtime-rag-answer-gate/038.R1/red.txt`
- Integration:
  `artifacts/slices/038-runtime-rag-answer-gate/038.R1/integration.txt`

## Completion Evidence

Status: completed on 2026-06-09.

Numbering was rechecked on 2026-06-09. 038 follows 037 and uses 035 retrieval
capabilities through runtime ports.

Evidence:

- RED:
  - `artifacts/slices/038-runtime-rag-answer-gate/038.1/red.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.2/red.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/red.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/red-browser-confidence.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/red-sop-low-rag.txt`
- Unit/integration:
  - `artifacts/slices/038-runtime-rag-answer-gate/038.1/unit.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.2/unit-integration.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/unit-integration-after-browser-fix.txt`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/unit-integration-after-sop-rag-order.txt`
- API E2E/regression:
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/final-targeted.txt`
  - Result: `40 passed, 1 warning`
- Browser UAT:
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/browser-uat-result.json`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/uat.md`
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/screenshots/browser-uat-rag.png`
- Full backend:
  - `artifacts/slices/038-runtime-rag-answer-gate/038.3/full-backend.txt`
  - Result: `465 passed, 8 skipped, 15 failed`; failures match existing
    unrelated runtime-lab scale/workflow baseline issues and are documented in
    the artifact.
