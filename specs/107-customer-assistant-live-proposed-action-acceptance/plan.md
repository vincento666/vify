# Plan: Customer Assistant Live Proposed Action Acceptance

## Slice 107.1 Proposed Action Safety Category

1. Add SDD docs and a RED expectation that the live gate requires
   `proposed_action_safety_boundaries`.
2. Add deterministic local-provider acceptance coverage for the fourth category.
3. Harden the live gate category list so a completed result missing the proposed
   action safety boundary fails closed.
4. Implement the proposed-action safety category by running the high-risk ReAct
   write path with a live tool call, then asserting the tool is not executed,
   a pending proposed action exists, and event evidence is persisted.
5. Run focused unit, acceptance, and lint gates.
6. Save evidence and commit the focused feature point.

## Test Strategy

- Unit: `tests/unit/customer_assistant/test_live_react_acceptance_gate.py`
- Acceptance: `tests/acceptance/test_customer_assistant_live_react_acceptance.py`
- Lint: `ruff check app/modules/customer_assistant/eval/live_react_acceptance.py tests/unit/customer_assistant/test_live_react_acceptance_gate.py tests/acceptance/test_customer_assistant_live_react_acceptance.py`

## Live Provider Command

```bash
HIFY_RUN_CUSTOMER_ASSISTANT_LIVE_REACT_ACCEPTANCE=1 \
HIFY_CUSTOMER_ASSISTANT_LIVE_API_KEY=<openai-compatible-key> \
HIFY_CUSTOMER_ASSISTANT_LIVE_BASE_URL=https://openrouter.ai/api/v1 \
rtk uv run pytest tests/acceptance/test_customer_assistant_live_react_acceptance.py::CustomerAssistantLiveReactAcceptanceTest::test_customer_assistant_live_react_acceptance
```

Optional model pool override:

```bash
HIFY_CUSTOMER_ASSISTANT_LIVE_MODEL_POOL=xiaomi/mimo-v2-flash,qwen/qwen3.5-9b,deepseek/deepseek-v4-flash
```

## Risk Notes

- The fourth category should reuse the existing live ReAct high-risk write path
  to avoid broadening live provider surface area.
- The artifact must not record API keys, authorization headers, tokens, or raw
  database URLs from provider-config bridge failures.
- If live credentials are unavailable, this slice is complete only as a
  preparatory deterministic gate; full live-provider validation remains blocked
  on operator-provided credentials.
