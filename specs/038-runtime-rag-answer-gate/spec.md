# Spec 038: Runtime RAG Answer Gate

## Goal

Add a controlled document RAG answer path to runtime-lab for long-tail knowledge
questions that are not FAQ answers and not SOP handling intents.

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
- document/chunk retrieval proposal gate using 035 retrieval options;
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
  -> 036/037 FAQ
  -> SOP/resume arbitration
  -> 038 RAG answer gate
  -> 039 Agent fallback / handoff escalation
```

RAG runs after SOP arbitration because document snippets are not valid SOP
targets. If the user clearly asks a knowledge question during active SOP, RAG
may answer without task mutation only when policy confidence is high.

## Acceptance Criteria

- long-tail document question returns `ANSWER_RAG` with citations;
- low retrieval confidence returns clarification or handoff according to policy;
- active SOP RAG answer preserves task state;
- RAG snippets never appear in SOP classifier candidates;
- generation is controlled by a port and can be fake/deterministic in CI;
- RAG answer can recommend but not directly create handoff unless 033 policy
  approves.

## Completion Capability

After 038, runtime-lab can answer long-tail knowledge questions with cited
evidence while keeping SOP routing deterministic and auditable.

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
