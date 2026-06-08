# RuntimeLab 034.12 Mixed Routing Summary

- Scope: booking/refund/change/consultation core airline scenarios.
- Natural scenario corpus: 40 cases, 10 per business area.
- Route coverage:
  - strong explicit/keyword routing: 40 natural single-SOP completion cases;
  - qwen LLM arbitration: 4 representative active-task switch journeys;
  - resume policy: single suspended task boundary, `RESUME_TASK` after completing
    the interrupted secondary SOP;
  - Chatflow LLM execution: qwen-backed `LLM` nodes in the representative live
    journeys.
- Live journey shape:
  `A start -> B switch -> B complete -> resume A -> A complete -> C start -> C complete`.
- Result:
  - non-live 40-case mixed routing contract: passed;
  - qwen live 4 representative three-SOP journeys: passed;
  - API key: runtime environment only, not recorded.

## Why Not Every Case Uses LLM Arbitration

The route engine should not force LLM arbitration when a natural utterance
contains a strong configured business signal. 034.12 therefore validates both
paths: strong explicit/keyword routing for ordinary high-confidence starts, and
qwen LLM arbitration for representative active-task switch decisions.
