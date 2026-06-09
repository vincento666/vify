# Plan 036: Runtime FAQ Exact Answer Gate

## Architecture

```text
RuntimeLabService
  -> HandoffPolicy from 033
  -> FaqExactAnswerGate
     -> KnowledgeFacade / FAQ repository boundary from 035
  -> SOP route arbitration
```

`FaqExactAnswerGate` returns a proposal, not a side effect:

```text
{
  action: ANSWER_FAQ,
  answer,
  confidence,
  margin,
  evidence,
  mutatesSopState: false
}
```

The runtime policy gate decides whether to accept, clarify, or continue to SOP
arbitration.

## TDD Strategy

RED tests first:

- FAQ exact answer route action is unsupported;
- no-active exact FAQ currently goes to SOP/clarify instead of `ANSWER_FAQ`;
- active SOP FAQ currently consumes message as a slot;
- ambiguous active SOP FAQ/business input currently lacks clarification;
- explicit handoff trigger must beat FAQ.

GREEN:

- add route action and payload shape;
- add FAQ exact/keyword proposal gate;
- add active-SOP safety guard;
- emit route evidence and events.

## SDD Gate

Each slice must update spec/tasks evidence:

```text
artifacts/slices/036-runtime-faq-exact-answer-gate/
  036.1/
  036.2/
  036.3/
```

No frontend change is required unless the existing 034 lab cannot show the
route action/evidence.

## Execution Result

036 was implemented as a single completion commit after all 036.1-036.3 gates
were green, rather than committing each internal sub-slice independently. This
keeps the stricter user gate intact: no work moves to 037 until 036 RED,
unit/integration, API E2E, and browser-control UAT evidence exists.

Final targeted gate:

```text
artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/final-targeted.txt
26 passed
```

Browser-control UAT:

```text
artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/uat.md
artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/browser-uat-result.json
```

Full backend pytest was attempted and documented at
`artifacts/slices/036-runtime-faq-exact-answer-gate/036.3/full-backend.txt`.
The remaining failures are pre-existing or outside 036's target surface.

## Non-Goals

- no semantic FAQ embeddings;
- no RAG generation;
- no Agent fallback;
- no human console UI.

## Unified Arbitration Refactor Gate

After the 2026-06-09 routing revision, 036 must no longer complete by answering
FAQ before central arbitration. It must create typed `ANSWER_FAQ` candidates
that join SOP/RAG/resume candidates in the same classifier payload.

The refactor is complete only when route evidence shows:

- `candidate_recall` includes FAQ and SOP candidates together when both match;
- `llm_intent_arbitration` receives the FAQ candidate;
- selected FAQ executes answer without task mutation;
- hard-stop handoff still exits before arbitration.
