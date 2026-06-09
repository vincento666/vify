# Spec 036: Runtime FAQ Exact Answer Gate

## Goal

Add the first FAQ candidate generator to runtime-lab: exact, normalized,
keyword, and high-confidence structured FAQ answer candidates controlled by the
runtime policy plane.

Architecture revision on 2026-06-09: 036 is no longer an independent early-exit
FAQ answer layer. It produces `ANSWER_FAQ` candidates for the unified candidate
pool. Except for 033 hard stops, final FAQ-vs-SOP decisions are made by central
constrained LLM arbitration plus PolicyGate.

## Dependency

Required before 036 implementation:

- 033 handoff action foundation complete;
- 035 Knowledge retrieval productization available for structured FAQ CRUD and
  source-aware retrieval;
- existing 030/032 SOP routing and 034 lab gates still pass.

## Scope

In scope:

- `ANSWER_FAQ` runtime route action;
- FAQ exact/normalized/keyword high-confidence candidate generation;
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
  -> unified hybrid candidate recall
       036 FAQ exact/high-confidence candidates
       037 semantic FAQ candidates
       SOP/resume candidates
       RAG/Agent candidates
  -> central constrained LLM arbitration
  -> PolicyGate
  -> typed executor
```

Active SOP exception:

```text
active SOP + clear safe FAQ question -> FAQ candidate may be selected as ANSWER_FAQ, no task mutation
active SOP + ambiguous FAQ/business input -> CLARIFY candidate may be selected, no task mutation
active SOP + slot answer -> CONTINUE_ACTIVE_SOP candidate may be selected
```

## Acceptance Criteria

- exact FAQ question creates `ANSWER_FAQ` candidate before central arbitration;
- keyword/high-confidence FAQ creates candidate when score and margin pass;
- active SOP FAQ answer does not change active task step, checkpoint, business
  refs, or suspended task list;
- active SOP ambiguous question vs slot input asks clarification;
- FAQ answer emits runtime evidence and event;
- FAQ hits appear as typed `ANSWER_FAQ` candidates in constrained classifier
  input, never as `SOP_INTENT` candidates;
- explicit handoff trigger still wins over FAQ;
- existing SOP routing regressions still pass.

## Completion Capability

After 036, runtime-lab can safely answer known FAQ questions, including inside
an active SOP, without damaging SOP state. The system can explain why a FAQ
answer was returned and prove the answer came from a structured FAQ source.

## Unified Arbitration Refactor Gate

Status: completed on 2026-06-09.

The previous 036 evidence proves the old early-exit FAQ gate. The current
architecture requires exact/keyword FAQ results to become candidate evidence for
central arbitration rather than independent final judges.

R1 evidence:

- RED:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.R1/red.txt`
- Integration:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.R1/integration.txt`
- Unified arbitration regression:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.R1/unified-arbitration-regression.txt`

## Specification Sign-off

Status: complete.

Numbering was rechecked on 2026-06-09. 036 follows the existing 035 Knowledge
Retrieval Productization spec and consumes its retrieval contracts without
duplicating knowledge-module implementation work.

## Completion Evidence

Completed on 2026-06-09 with the following gates:

- RED:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.1/red.txt`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/red.txt`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/red-knowledge-gate.txt`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/red.txt`
- Unit/integration:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.1/unit.txt`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.2/unit-integration.txt`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/unit-integration.txt`
- Runtime-lab API E2E and regression:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/final-targeted.txt`
  (`26 passed`)
- Browser UAT through Swagger UI:
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/uat.md`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/browser-uat-result.json`,
  `artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/screenshots/browser-uat-faq.png`

Full backend pytest was attempted and saved to
`artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/full-backend.txt`.
It produced `451 passed, 8 skipped, 15 failed`; the observed failures are
outside the 036 target gate, including existing runtime-lab chatflow-adapter
host resolution failures and workflow knowledge-facade stub signature drift.
