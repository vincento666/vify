# 184.2 Phase 1 Sandbox And Approval Boundary

## Modification Scope

- Added `app/modules/ai_assistant/domain/permissions.py`.
- Added `app/modules/ai_assistant/domain/sandbox.py`.
- Extended Tool Registry with protected `update_customer_profile` and blocked
  `run_shell` manifests.
- Added MySQL8 tables for approvals and proposed actions.
- Extended repository, harness service, and API router with approval queue,
  approve, deny, sandbox-denied, and proposed-action event behavior.
- Added unit, contract, and E2E tests for the security boundary.

## RED Evidence

- `red.txt`: 9 expected failures before implementation.
- Unit failures showed missing `permissions` and `sandbox` modules.
- Contract failures showed missing approvals API, missing approval-required
  behavior, and shell commands incorrectly completing.

## Implementation Summary

- `smart_approval` auto-approves read-only tools.
- High-risk business writes create `approval.required` and
  `proposed_action.created` events, persist approval/proposed-action rows, and
  pause the run in `WAITING_APPROVAL`.
- Denied approvals record actor, reason, and `approval.denied` without
  executing the tool.
- Approved approvals record actor and `approval.granted`; Phase 1 still does
  not execute high-risk business writes automatically.
- `run_shell` is blocked by `SandboxPolicy` and emits `sandbox.denied`.
- Production `always_approve` is denied by policy.

## Gates Run

- `unit.txt`: `4 passed`
- `integration.txt`: `2 passed`
- `contract.txt`: `5 passed, 1 warning`
- `e2e.txt`: `1 passed, 1 warning`
- `focused.txt`: `16 passed, 1 warning`
- `lint.txt`: `All checks passed`
- `mypy.txt`: `Success: no issues found in 13 source files`
- `mysql8-boundary.txt`: `2 passed`

MySQL8 test database:

```text
HIFY_MYSQL8_TEST_DATABASE_URL=mysql+pymysql://hify:hify@127.0.0.1:3316/hify?charset=utf8mb4
HIFY_MYSQL8_TEST_ADMIN_DATABASE_URL=mysql+pymysql://root:root@127.0.0.1:3316/mysql?charset=utf8mb4
```

## Remaining Risk

- Phase 1 approval grant records the decision but intentionally does not
  execute high-risk business writes; later specs must define safe execution.
- Browser UAT and remScaleClosure are not applicable until frontend slices.
- Starlette TestClient deprecation warning remains from existing dependency
  stack.
