# Tasks — Spec 215

证据根目录：`artifacts/slices/215-runtime-dag-frontier-scheduler/<slice>/`

## Slice 215.1 — Node state graph & frontier computation (pure function)

- [ ] RED：写 `tests/unit/runtime/scheduler/test_frontier_computation.py`，断言 `compute_frontier(graph, state)` 返回正确 runnable / waiting / skipped；当前应红；证据 `artifacts/215.1/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime/scheduler -q` 全绿；证据 `artifacts/215.1/unit.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿；证据 `artifacts/215.1/contract.txt`
- [ ] Docs：在 `docs/runtime/dag-semantics.md` 补 "frontier algorithm" 小节
- [ ] Git commit：`feat(runtime): introduce frontier computation pure function`

## Slice 215.2 — Replace single-path while-loop with frontier scheduler (sequential parity)

- [ ] RED：写 `tests/integration/runtime/test_frontier_scheduler_sequential_parity.py`，跑现有顺序链路并断言行为字节级相同（事件序列、节点完成顺序）；当前应红；证据 `artifacts/215.2/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/215.2/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/215.2/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/workflow-six-node-matrix.mjs`、`rtk node frontend/e2e/chatflow-channels.mjs` 全绿；证据 `artifacts/215.2/e2e.txt`
- [ ] Docs：spec.md 标记 scheduler 已切换
- [ ] Git commit：`refactor(runtime): adopt frontier scheduler for sequential graphs`

## Slice 215.3 — Concurrent fan-out & scope isolation

- [ ] RED：写 `tests/integration/runtime/test_concurrent_fanout.py` 与 `tests/unit/runtime/test_scope_isolation.py`，断言 N 个无依赖下游并发完成且 scope 不串扰；当前应红；证据 `artifacts/215.3/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/215.3/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/215.3/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿；证据 `artifacts/215.3/contract.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-scoped-variables-history.mjs`、`rtk node frontend/e2e/workflow-variable-aggregation-assignment.mjs` 全绿；证据 `artifacts/215.3/e2e.txt`
- [ ] Git commit：`feat(runtime): execute frontier nodes concurrently with scope isolation`

## Slice 215.4 — State propagation, implicit join, side-effect terminal, run completion

- [ ] RED：写 `tests/contract/runtime_dag/test_state_propagation.py`、`tests/integration/runtime/test_terminal_side_effect.py`、`tests/integration/runtime/test_run_completion.py`；当前应红；证据 `artifacts/215.4/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/215.4/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿；证据 `artifacts/215.4/contract.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-running-path-animation.mjs`、`rtk node frontend/e2e/chatflow-runtime-timeline-ui.mjs` 全绿；证据 `artifacts/215.4/e2e.txt`
- [ ] Browser UAT：跑包含 side-effect terminal leaf 的 Chatflow 草图，截图无 "Next node not found"；证据 `artifacts/215.4/uat.md`
- [ ] Git commit：`feat(runtime): propagate node states and finish runs by active path`

## Slice 215.5 — Failure strategies: fail-fast / continue-on-error / error branch / partial success

- [ ] RED：写 `tests/contract/runtime_dag/test_failure_strategies.py`，4 类策略各一个 case；当前应红；证据 `artifacts/215.5/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/215.5/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/215.5/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿；证据 `artifacts/215.5/contract.txt`
- [ ] Docs：在 dag-semantics.md 增补 "failure strategy matrix"
- [ ] Git commit：`feat(runtime): implement failure strategy matrix in scheduler`

## Slice 215.6 — Event sequence monotonicity under concurrency

- [ ] RED：写 `tests/contract/runtime/test_event_sequence_monotonic.py`，压并发 10+ 节点同时完成；当前应红；证据 `artifacts/215.6/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime -q` 全绿；证据 `artifacts/215.6/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/215.6/integration.txt`
- [ ] Docs：在 dag-semantics.md 增补 "event sequence guarantee"
- [ ] Git commit：`feat(runtime): guarantee monotonic event sequence under concurrency`

## Slice 215.7 — Regression on spec 212 + 213 + 214 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：三 spec 入口套件重跑全绿；证据 `artifacts/215.7/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212.5 / 214.5 全套；证据 `artifacts/215.7/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 215 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 215 exit regression`
