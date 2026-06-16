# Plan: Runtime V2 Long-Run Lifecycle Evidence

## Slice 114.1

Prove the runtime v2 long-run lifecycle through backend API integration tests only.

## Approach

1. Create a small Chatflow runtime v2 fixture with `START -> QUESTION -> END`.
2. Start a run and let the background runtime interrupt on `QUESTION`.
3. Close the first client context, open a new client, query the run, replay events, and resume from the durable checkpoint.
4. Start a second interrupted run, close the client, open another client, cancel the run, and verify terminal state/event/checkpoint durability.
5. Keep implementation scoped to runtime v2 event/checkpoint evidence if the RED test reveals missing API data.

## Test Strategy

- Focused integration test: `tests/integration/workflow/test_runtime_v2_long_run_lifecycle.py`.
- Regression coverage: existing runtime v2 workflow/chatflow facade tests.
- Static gate: `ruff check` for touched Python files.

## Browser UAT

Not required for this slice because no user-visible frontend workflow route behavior is added or changed.

## Risks

- Runtime v2 completion is asynchronous, so tests must poll terminal/interrupted state with a timeout.
- The slice uses two runs because a successfully resumed run is already terminal and should not later be cancelled.
