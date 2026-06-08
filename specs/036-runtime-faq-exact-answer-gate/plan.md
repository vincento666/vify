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

## Non-Goals

- no semantic FAQ embeddings;
- no RAG generation;
- no Agent fallback;
- no human console UI.
