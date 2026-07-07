# Runtime V2 Target Gap Audit

Date: 2026-07-07

Branch:

```text
codex/runtime-v2-closure-replay
```

Base:

```text
d6fc969c feat(ai-assistant): complete harness MVP gates
```

## Result

No open blocker found after the focused spec 213 async-default replay fix.

## Gap Matrix

| Target gap | Status | Evidence |
| --- | --- | --- |
| DAG multi-path / Coze-Eino semantics | PASS | `tests/contract/runtime_dag`, `tests/integration/runtime/test_concurrent_fanout.py`, `test_run_completion.py`, `test_terminal_side_effect.py`, `test_frontier_scheduler_sequential_parity.py`: 15 passed |
| Async-first default | FIXED | `213.async-default-replay/red.txt`, `unit.txt`, `integration.txt`; Runtime Lab SOP default changed from `sync` to `async`; explicit sync fallback remains configurable |
| SOP Router light ledger | PASS | `test_runtime_lab_sop_state_boundary.py`, `test_sop_router_ledger_schema.py`, `test_no_state_mirroring.py`, `test_aggregate_from_child_chatflow.py`, `test_sop_uat_matrix_manifest.py`: 13 passed, 20 subtests |
| Production job scheduler | PASS | `tests/contract/runtime_jobs`, `tests/integration/runtime_jobs`, DB pool tests: 20 passed |
| DB pool / connection factory | PASS | `test_pool_config.py`, `test_database_factory.py`: covered in job scheduler gate |
| Event stream, cancel, rate limit, backpressure | PASS | SSE reconnect, concurrency limits, queue states, event compaction, outbox compensation, cooperative cancel, external-call governance: 14 passed |
| Runtime Ops module | PASS | Runtime Ops backend contracts: 4 passed; frontend Runtime Ops tests: 12 passed; rem gate: 1 passed |
| Capacity / fault acceptance | PASS | `tests/integration/runtime/load`, `tests/integration/runtime/chaos`: 13 passed |
| Spec 222 protection | PASS | protected-path diff empty; 222 backend smoke 19 passed; 222 frontend smoke 28 passed |

## Notes

- `branching_edges` still appears only as an unsupported pattern for illegal
  fan-out without explicit `allowFanOut`; explicit default fan-out and branch
  multi-target paths are covered by passing runtime DAG tests.
- `runtime_lab_sop_runtime_invocation_mode="sync"` remains available as an
  explicit fallback override. It is no longer the default.
- Full merge gate still requires target-branch clean check and final verifier
  rerun before merge.
