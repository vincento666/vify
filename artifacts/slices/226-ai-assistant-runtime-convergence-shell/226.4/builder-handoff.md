# Builder Handoff — 226.4

TDD method: `tdd`

## Scope

- Added explicit local-header and trusted-state principal resolvers. Production
  configuration now requires trusted state and rejects arbitrary identity
  headers.
- Added host product permissions: `ai_assistant:read` for reads and
  `ai_assistant:operate` for mutations. Local-header mode remains an explicit
  development compatibility adapter.
- Stopped using request body `actorId` as identity truth. Approval and control
  events persist the server principal plus whether the deprecated field was
  absent, matched, or mismatched.
- Wired deployment environment into approval policy so production
  `always_approve` fails closed.
- Added tenant to durable AI Assistant session, run, memory cursor/completion,
  and model-usage scopes, with reversible Alembic revision 0036.
- Enforced tenant/user/workspace at repository reads and writes for run
  messages, events, approvals, tool calls, operations, attempts, and memory.
- Persisted a versioned execution-scope snapshot with each run. The standalone
  handler reconstructs repository scope from the durable run and verifies the
  runtime job owner is the run's session.
- Added a recursive secret-free runtime-job payload guard. Raw credential-like
  fields are rejected before insert/requeue; explicit references remain valid.
- Removed the default link-only child bridge. Child capability now fails closed
  until 226.6 supplies a real scoped lifecycle provider.
- Corrected completion event ordering: final checkpoint is durable before the
  worker heartbeat announces completion.

## RED

- `red-trusted-principal.txt`
- `red-actor-audit.txt`
- `red-permission-policy.txt`
- `red-scope.txt`
- `red-secret-free-job.txt`

## GREEN Evidence

```text
rtk uv run pytest tests/unit/ai_assistant/test_permission_policy.py tests/contract/ai_assistant/test_trusted_principal.py tests/integration/ai_assistant/test_scope_authorization.py tests/integration/ai_assistant/test_approval_actor_audit.py -q --tb=short
7 passed

rtk uv run pytest tests/contract/ai_assistant/test_tenant_scope_migration.py tests/contract/runtime_jobs/test_owner_identity_migration.py tests/contract/runtime_jobs/test_secret_free_payload.py tests/integration/runtime_jobs/test_ai_assistant_runtime_job_handler.py -q --tb=short
8 passed

rtk uv run pytest tests/unit/ai_assistant/test_resource_lock.py tests/contract/test_ai_assistant_security_api.py -q --tb=short
19 passed

rtk uv run pytest tests/contract/test_ai_assistant_session_runtime_api.py -q --tb=short
8 passed

rtk uv run pytest tests/unit/ai_assistant tests/unit/core/test_config.py tests/unit/architecture tests/contract/ai_assistant tests/contract/test_ai_assistant*.py tests/integration/ai_assistant -q
233 passed, 21 subtests passed

rtk zsh -c 'PYTHONPATH=. uv run alembic heads'
0036_ai_assistant_tenant_scope (head)

rtk uv run ruff check <226.4 scoped paths>
All checks passed

rtk git diff --check
PASS
```

## Security Review

- Critical: none found.
- High: none found.
- Closed during review: dependent approval/proposed-action writes initially
  lacked repository scope predicates; negative cross-tenant tests now cover
  them.
- Preserved boundary: resource locks intentionally accept opaque/synthetic
  owners and remain global coordination primitives; they are not tenant data
  records.
- Residual low risk: local-header mode trusts headers by design. Production
  configuration validation prevents that mode.

## Explicit Gate Notes

- Browser UAT / frontend / rem / build: N/A. No frontend behavior changed.
- Live provider: N/A. Provider-call budget remained zero.
- Production migration/deploy: N/A and not authorized. Upgrade/downgrade and
  clean-head behavior were tested on disposable MySQL only.
- Child lifecycle: fail-closed removal is in scope; real child execution remains
  226.6 and is not claimed here.
- Full independent fresh-context review: not required by the standard review
  context. Checker and Reviewer evidence is read-only and does not claim fresh
  context.

## Remaining Contract

- Router-local autonomous execution and frontend `/worker/process` compatibility
  remain until 226.5 replaces them with durable standalone-worker flow.
- Lease fencing, takeover, cancellation, short-session SSE, and bounded
  backpressure remain 226.5.
- Stable activity projection, real child lifecycle, and product shell remain
  226.6/226.7.
