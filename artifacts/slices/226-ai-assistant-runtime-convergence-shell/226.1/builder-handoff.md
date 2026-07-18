# Builder Handoff — 226.1

TDD method: `tdd`

## Scope

- Added the product-neutral `app.modules.agent_harness` public Module.
- Added the `AgentHarness.execute(HarnessRunRequest, HarnessProfile)` tracer.
- Converted `RestrictedReactWorker` into a Customer Assistant Adapter over the
  shared Harness while preserving `TaskItem`, `WorkerResult`, proposed-action,
  error, and event-schema behavior.
- Added public Interface, Adapter, and dependency-direction contract tests.

## RED

See `red-public-interface.txt`.
Reviewer repair RED is recorded in `reviewer-repair-red.txt`.

Additional Adapter RED:

```text
TypeError: RestrictedReactWorker.__init__() got an unexpected keyword argument 'harness'
```

Observed with:

```text
rtk uv run pytest tests/contract/agent_harness/test_customer_assistant_adapter.py -q --tb=short
```

## GREEN Evidence

```text
rtk uv run pytest tests/contract/agent_harness tests/unit/customer_assistant/test_react_worker.py -q --tb=short
11 passed

rtk uv run pytest tests/integration/customer_assistant/test_react_worker_integration.py tests/integration/customer_assistant/test_worker_profiles.py tests/e2e/customer_assistant/test_customer_assistant_react_worker_sse.py -q --tb=short
13 passed, 9 subtests passed

rtk uv run pytest tests/integration/customer_assistant -q --tb=short
90 passed, 1 skipped, 14 subtests passed

rtk uv run ruff check app/modules/agent_harness app/modules/customer_assistant/domain/react_worker.py tests/contract/agent_harness
All checks passed
```

## Explicit N/A Gates

- Browser UAT: N/A. This foundation slice changes no frontend or public user
  interaction; the existing Customer Assistant SSE E2E is the applicable
  end-to-end gate.
- Database migration: N/A. No schema or persistence contract changed.
- Live provider: N/A. Contract budget is zero and deterministic profiles cover
  this slice.

## Safety

- No production data, migration apply, deployment, provider call, push, PR, or
  merge action occurred.
- Pre-existing unrelated worktree changes were not staged, rewritten, or
  removed.
