# Tasks — Spec 215

证据根目录：`artifacts/slices/215-runtime-dag-frontier-scheduler/<slice>/`

## Slice 215.1 — Node state graph & frontier computation (pure function)

- [x] RED：写 `tests/unit/runtime/scheduler/test_frontier_computation.py`，断言 `compute_frontier(graph, state)` 返回正确 runnable / waiting / skipped；红于缺少 `app.modules.runtime.domain.scheduler`；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.1/red.txt`
- [x] Unit：`rtk uv run pytest tests/unit/runtime/scheduler -q` 全绿（`3 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.1/unit.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿（`8 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.1/contract.txt`
- [x] Docs：在 `docs/runtime/dag-semantics.md` 补 "Frontier Algorithm" 小节；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.1/docs-check.txt`
- [x] Git commit：`feat(runtime): introduce frontier computation pure function`

## Slice 215.2 — Replace single-path while-loop with frontier scheduler (sequential parity)

- [x] RED：写 `tests/integration/runtime/test_frontier_scheduler_sequential_parity.py`，跑现有顺序链路并断言行为字节级相同（事件序列、节点完成顺序）；红于 runtime_v2 尚未导入/调用 `compute_frontier`；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.2/red.txt`
- [x] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿（`4 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.2/unit.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿（`7 passed`）；补跑 runtime-v2 facade regression 全绿（`10 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.2/integration.txt` / `integration-runtime-v2-regression.txt`
- [x] E2E：`rtk node frontend/e2e/workflow-six-node-matrix.mjs`、`rtk node frontend/e2e/chatflow-channels.mjs` 全绿；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.2/e2e.txt`
- [x] Docs：spec.md 标记 scheduler 已切换；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.2/docs-check.txt`
- [x] Git commit：`refactor(runtime): adopt frontier scheduler for sequential graphs`

## Slice 215.3 — Concurrent fan-out & scope isolation

- [x] RED：写 `tests/integration/runtime/test_concurrent_fanout.py` 与 `tests/unit/runtime/test_scope_isolation.py`，断言 N 个无依赖下游并发完成且 scope 不串扰；红于缺少 context clone helper / compatibility 拒绝显式 fan-out；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.3/red.txt` / `red-integration-fanout.txt`
- [x] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿（`5 passed`）；补跑 runtime_v2 core 全绿（`8 passed, 6 subtests passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.3/unit.txt` / `unit-workflow-runtime-v2.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿（`8 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.3/integration.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿（`8 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.3/contract.txt`
- [x] E2E：`rtk node frontend/e2e/chatflow-scoped-variables-history.mjs`、`rtk node frontend/e2e/workflow-variable-aggregation-assignment.mjs` 全绿；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.3/e2e.txt`
- [x] Git commit：`feat(runtime): execute frontier nodes concurrently with scope isolation`

## Slice 215.4 — State propagation, implicit join, side-effect terminal, run completion

- [x] RED：写 `tests/contract/runtime_dag/test_state_propagation.py`、`tests/integration/runtime/test_terminal_side_effect.py`、`tests/integration/runtime/test_run_completion.py`；红于 join `selectionState` 丢失 selected/skipped upstream；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.4/red.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿（`10 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.4/integration.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿（`9 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.4/contract.txt`
- [x] E2E：`rtk node frontend/e2e/chatflow-running-path-animation.mjs`、`rtk node frontend/e2e/chatflow-runtime-timeline-ui.mjs` 全绿；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.4/e2e.txt`
- [x] Frontend rem/full unit：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`（`1 passed`）和完整 `test:unit`（`99 passed / 433 tests`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.4/rem.txt` / `frontend-unit.txt`
- [x] Browser UAT：跑包含 side-effect terminal leaf 的 Chatflow 草图，截图无 "Next node not found"；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.4/uat.md`
- [x] Git commit：`feat(runtime): propagate node states and finish runs by active path`

## Slice 215.5 — Failure strategies: fail-fast / continue-on-error / error branch / partial success

- [x] RED：写 `tests/contract/runtime_dag/test_failure_strategies.py` 与 partial 集成 fixture，4 类策略各一个 case；红于 `partial` 未被 contract/runtime 支持；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.5/red.txt`
- [x] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿（`5 passed`）；补跑 runtime v2 core（`8 passed, 6 subtests passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.5/unit.txt` / `unit-workflow-runtime-v2.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿（`11 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.5/integration.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿（`11 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.5/contract.txt`
- [x] Docs：在 dag-semantics.md 增补 "Failure Strategy Matrix"；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.5/docs-check.txt`
- [x] Git commit：`feat(runtime): implement failure strategy matrix in scheduler`

## Slice 215.6 — Event sequence monotonicity under concurrency

- [x] RED：写 `tests/contract/runtime/test_event_sequence_monotonic.py`，压并发 12 个节点同时完成；红于 MySQL `(run_id, sequence)` 唯一索引冲突；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.6/red.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime/test_event_sequence_monotonic.py -q` 与完整 `rtk uv run pytest tests/contract -q` 全绿（`1 passed` / `117 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.6/contract-targeted.txt` / `contract.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿（`11 passed`）；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.6/integration.txt`
- [x] Docs：在 dag-semantics.md 增补 "Event Sequence Guarantee"；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.6/docs-check.txt`
- [x] Git commit：`feat(runtime): guarantee monotonic event sequence under concurrency`

## Slice 215.7 — Regression on spec 212 + 213 + 214 entry gates

- [x] RED：旧显式 fan-out 集成契约仍按 spec 214 前语义期待拒绝，Runtime Lab scale 在 resume 后卡在 `COMPLETE_TASK`；补充 v2 bridge resume 红测复现 raw `SUCCEEDED` node-run 未被 frontier resume 识别为 completed；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/red-integration-outdated-contract.txt` / `red-v2-bridge-resume.txt` / `e2e-red.txt`
- [x] Unit / Integration / Contract / Frontend / rem：三 spec 入口套件重跑全绿；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/unit.txt`（`422 passed, 2 skipped`）、`integration.txt`（`491 passed, 10 skipped`）、`contract.txt`（`117 passed`）、`frontend-unit.txt`（`99 passed / 433 tests`）、`rem.txt`（`1 passed`）
- [x] Browser UAT：spec 212.5 / 214.5 全套全绿，包含 14 条 Chatflow/Workflow browser scripts + Runtime Lab scale `15 scenarios, 5 switches`；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/e2e.txt` / `uat.md`
- [x] Docs：在 baseline.md 追记 "spec 215 exit @ slice commit `test(runtime): seal spec 215 exit regression`"；证据 `artifacts/slices/215-runtime-dag-frontier-scheduler/215.7/docs-check.txt`
- [x] Git commit：`test(runtime): seal spec 215 exit regression`
