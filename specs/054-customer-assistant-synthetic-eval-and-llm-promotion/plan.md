# Plan 054: Customer Assistant Synthetic Eval And LLM Promotion Readiness

## Implementation Shape

Extend the existing 051 eval module rather than adding a new framework.

Recommended additions:

```text
app/modules/customer_assistant/eval/
  synthetic_cases.py
  promotion_report.py
  browser_uat_scenarios.py
tests/unit/customer_assistant/test_synthetic_eval_cases.py
tests/integration/customer_assistant/test_llm_promotion_readiness.py
```

## Scenario Matrix

Build cases from a small matrix:

- actor: customer, operator, system;
- intent: refund, baggage, combined, cancel, ambiguous;
- risk: read-only, proposed-write, unsafe-direct-write;
- runtime result: completed, waiting, failed, timed-out fixture;
- event expectation: L1 only, L1 plus L2 worker events.

## Database Readiness

Add a small readiness probe that can run against SQLite during tests and MySQL 8
when the migration branch is available:

```text
refund_ticket binding exists
bound chatflow row exists
bound chatflow is publishable/runnable or fallback mode is explicit
```

The readiness report should distinguish:

- runtime bug;
- missing seed data;
- intentionally mocked fallback.

## Gates

Default gates must run without network access.

Optional live gate:

```text
HIFY_CUSTOMER_ASSISTANT_LIVE_PROMOTION_UAT=1
HIFY_CUSTOMER_ASSISTANT_LLM_SHADOW_MODEL_CONFIG_ID=<id>
```

Live gate can produce evidence, but it must not be required for default CI.

## Browser UAT

Use the 046 operator panel:

1. open `/customer-assistant`;
2. submit a refund request;
3. submit baggage QA;
4. submit a combined request;
5. test proposed action confirmation/execution mock;
6. verify progress checklist, task ledger, recommendation, draft, proposed
   action panel, and event timeline.
7. record active Chatflow data strategy: seeded DB, imported fixture, or
   explicit fallback mock.

## Output

The final artifact is a readiness report:

```text
artifacts/slices/054-customer-assistant-synthetic-eval-and-llm-promotion/report.md
```

It must state whether Spec 055 can start.
