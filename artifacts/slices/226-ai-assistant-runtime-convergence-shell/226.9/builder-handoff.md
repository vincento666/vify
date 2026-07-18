# Builder Handoff — 226.9

TDD method: `tdd`

## Scope

226.9 is the exit-only slice for Spec 226. It adds no production feature and
changes no runtime behavior.

The full AI Assistant exit sweep exposed two integration fixtures that still
relied on demo tools from the former implicit production registry:

- approval actor audit required `update_customer_profile`;
- scheduler metadata required `echo_context`.

Both tests now opt into `ToolRegistry.with_demo_tools()` explicitly. This keeps
the production registry fail-closed while retaining the intended integration
coverage.

## Exit Results

- AI Assistant full unit/contract/integration/E2E/eval sweep:
  `278 passed, 3 skipped, 2 failed, 21 subtests passed` on the first run.
  The only failures were the two stale demo-tool fixtures above. After the
  fixture correction, the complete AI Assistant integration suite passed:
  `35 passed`. No other failure was observed.
- Customer Assistant full affected suite:
  `166 passed, 2 skipped, 15 subtests passed`.
- Security matrix: `35 passed, 4 subtests passed`.
- HA/fault matrix: `47 passed`.
- public Agent Harness/Execution and product Adapter boundaries: `13 passed`.
- Runtime V2 unit and contract suites:
  `24 passed`, `31 passed`, `15 passed`, `13 passed`.
- Runtime V2 full integration suite, run exclusively:
  `35 passed` in `222.58s`.
- frontend full unit suite: `116 files / 482 tests passed`.
- frontend `vue-tsc && vite build`: PASS.
- Browser UAT: PASS against the Hify light shell.
- isolated migration contracts: `3 passed`; both 0035 and 0036 execute
  upgrade/downgrade, and a clean isolated database passes Alembic `check`.
- `PYTHONPATH=. alembic heads`: one head,
  `0036_ai_assistant_tenant_scope`.
- Ruff, `git diff --check`, dependency audit and added-line secret scan: PASS.

The three skipped tests are live-provider gates. The contract provider-call
budget is zero, so they remain explicit N/A rather than being represented as
production-provider evidence.

## Runtime Timing Diagnosis

The first parallel exit invocation produced one failure in
`test_true_parallel_fanout`: `1.709s` against a `<1.7s` wall-clock threshold.
A focused retry while other MySQL suites were still active took `1.837s`.

No workflow scheduler or timing assertion changed relative to parent
`cae5a5a9`. The same focused test passed in a detached parent worktree and then
passed on current HEAD after load was removed. The final exclusive full runtime
integration suite passed all 35 tests. This is recorded as test-environment
database contention; neither the threshold nor production code was weakened.

## Migration Boundary

Running repository-level `alembic check` against the configured shared/dev
database reported that the target database was not at head. Spec 226 explicitly
does not authorize applying migrations to a shared or production database.

Migration correctness is instead verified in disposable MySQL databases:

- 0035 owner identity upgrades, checks the owner-aware unique key, downgrades,
  and restores the legacy key;
- an isolated database upgrades to head and passes Alembic `check`;
- 0036 tenant scope upgrades, verifies columns/indexes, and downgrades.

Applying 0035/0036 to an actual environment remains a release/deployment action,
not an open implementation defect.

## Compatibility And N/A

- `/worker/process` physical deletion remains gated on external-consumer
  inventory. The compatibility endpoint is enqueue/inspect only and advertises
  the 2026-08-01 removal target.
- real external model/provider validation: N/A by the frozen zero-call budget.
- production multi-host load/SLA and OS/container sandbox certification: outside
  the MVP contract.
- production migration, deploy, push and merge: not authorized.
