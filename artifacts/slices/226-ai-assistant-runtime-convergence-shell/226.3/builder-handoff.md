# Builder Handoff — 226.3

TDD method: `tdd`

## Scope

- Moved the durable repository and worker state machine from Workflow into the
  product-neutral Runtime Module and updated all repository callers.
- Added a fail-closed `RuntimeJobHandlerRegistry`.
- Added a Runtime composition root that registers Workflow, Chatflow, and AI
  Assistant Adapters. Product imports are allowed only in composition; Runtime
  domain/infra stay product-neutral.
- Changed runtime job identity to `(owner_type, run_id, job_type)` in metadata,
  repository lookup, and reversible Alembic migration 0035.
- Added an AI Assistant standalone handler and proved it can claim and complete
  a persisted deterministic QUEUED run against disposable MySQL.
- Updated the standalone CLI to `workflow|chatflow|ai-assistant|both|all`; the
  script imports composition rather than product builders.
- Updated operations documentation without claiming the later durable enqueue
  and HA slice is complete.
- Made Alembic autogeneration exclude relational vector tables on MySQL,
  matching migrations 0002/0015 where those tables are intentionally absent.

## RED

- `red-owner-identity.txt`
- `red-module-boundary.txt`
- `red-handler-registry.txt`

## GREEN Evidence

```text
rtk uv run pytest tests/unit/workflow/test_runtime_job_worker.py tests/contract/runtime_jobs tests/integration/runtime_jobs -q --tb=short
30 passed

rtk uv run pytest tests/contract/test_workflow_runtime_job_gateway.py tests/integration/runtime/test_debug_runs_default_async.py tests/contract/test_chatflow_runtime_job_worker_gateway.py tests/contract/test_runtime_job_safe_retry.py tests/contract/runtime/test_idempotency_layers.py tests/contract/runtime/test_safe_action_audit.py -q --tb=short
13 passed

rtk uv run pytest tests/contract/runtime_jobs/test_owner_identity_migration.py -q --tb=short
2 passed

rtk zsh -c 'PYTHONPATH=. uv run alembic heads'
0035_runtime_job_owner_identity (head)

rtk uv run ruff check <226.3 scoped paths>
All checks passed

rtk git diff --check
PASS
```

## Explicit Gate Notes

- Configured local DB `alembic check`: ENV-BLOCKED because that database is
  below head. Applying 0035 to the user's configured database was not
  authorized. A disposable MySQL database passed upgrade, downgrade, and
  `command.check`.
- Browser UAT: N/A. No frontend behavior changed.
- Live provider: N/A. AI handler integration uses deterministic execution and
  contract provider budget remains zero.
- Production deployment/migration apply: N/A and not authorized.

## Remaining Contract

- `messages/async` still does not enqueue `AI_ASSISTANT` runtime jobs.
- Router in-process execution, lease fencing across domain writes, cancellation,
  short-session SSE, and bounded external I/O remain 226.5.
- Trusted principal/scope and secret-free job payload remain 226.4.
