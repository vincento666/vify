# Spec 036: Runtime FAQ Exact Answer Gate

## Goal

Add the first FAQ answer gate to runtime-lab: exact, normalized, keyword, and
high-confidence structured FAQ answers controlled by the runtime policy plane.

036 is the safe, low-cost answer layer before semantic FAQ, RAG, and fallback
Agent. It must answer clear FAQ questions without entering SOP arbitration, and
it must preserve active SOP state when a user asks a safe FAQ during a business
flow.

## Dependency

Required before 036 implementation:

- 033 handoff action foundation complete;
- 035 Knowledge retrieval productization available for structured FAQ CRUD and
  source-aware retrieval;
- existing 030/032 SOP routing and 034 lab gates still pass.

## Scope

In scope:

- `ANSWER_FAQ` runtime route action;
- FAQ exact/normalized/keyword high-confidence answer gate;
- FAQ evidence payload: FAQ id, question, answer, score, match type, source;
- active-SOP safe answer behavior with no slot consumption and no task mutation;
- ambiguity handling: question-vs-business-handling conflict returns
  `ASK_CLARIFICATION`/`CLARIFY`, not SOP collection;
- runtime-lab API response evidence and events.

Out of scope:

- FAQ vector/embedding semantic recall;
- document RAG answer generation;
- fallback Agent;
- frontend UI beyond existing 034 lab evidence display if already sufficient;
- handoff implementation beyond using 033 when explicit triggers fire.

## Routing Position

```text
033 hard handoff triggers
  -> 036 FAQ exact/high-confidence gate
  -> 037 semantic FAQ gate
  -> SOP/resume recall and LLM arbitration
  -> later RAG/Agent layers
```

Active SOP exception:

```text
active SOP + clear safe FAQ question -> ANSWER_FAQ, no task mutation
active SOP + ambiguous FAQ/business input -> CLARIFY, no task mutation
active SOP + slot answer -> CONTINUE_ACTIVE_SOP
```

## Acceptance Criteria

- exact FAQ question answers before SOP arbitration when no hard handoff trigger
  exists;
- keyword/high-confidence FAQ answers can answer when score and margin pass;
- active SOP FAQ answer does not change active task step, checkpoint, business
  refs, or suspended task list;
- active SOP ambiguous question vs slot input asks clarification;
- FAQ answer emits runtime evidence and event;
- FAQ hits never appear inside constrained SOP intent classifier candidates;
- explicit handoff trigger still wins over FAQ;
- existing SOP routing regressions still pass.

## Completion Capability

After 036, runtime-lab can safely answer known FAQ questions, including inside
an active SOP, without damaging SOP state. The system can explain why a FAQ
answer was returned and prove the answer came from a structured FAQ source.

## Specification Sign-off

Status: ready for implementation.

Numbering was rechecked on 2026-06-09. 036 follows the existing 035 Knowledge
Retrieval Productization spec and consumes its retrieval contracts without
duplicating knowledge-module implementation work.
