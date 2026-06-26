# Tasks — Spec 214

证据根目录：`artifacts/slices/214-runtime-dag-multipath-semantics/<slice>/`

## Slice 214.1 — DAG semantics doc & Pydantic schema

- [ ] RED：写 `tests/contract/runtime_dag/test_dag_schema.py`，断言 `EdgeSpec / PortSpec / BranchGroupSpec / NodeSelectionState / FinalOutputRule` 等模型存在并满足约定字段；当前应红；证据 `artifacts/214.1/red.txt`
- [ ] GREEN：在 `app/modules/workflow/api/schemas.py` / `app/modules/runtime/api/schemas.py` 落实 schema
- [ ] Unit：`rtk uv run pytest tests/unit/workflow -q`、`tests/unit/runtime -q` 全绿；证据 `artifacts/214.1/unit.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿；证据 `artifacts/214.1/contract.txt`
- [ ] Docs：新增 `docs/runtime/dag-semantics.md`，覆盖 edge / port / branch / skipped / terminal / final-output 全部子节
- [ ] Git commit：`feat(runtime): define DAG multipath semantics schema`

## Slice 214.2 — Canvas validation: fan-out, branch, side-effect terminal, implicit join, island

- [ ] RED：写 `tests/unit/workflow/validation/test_dag_canvas_rules.py`，准备 5 类图（合法 fan-out / 合法多分支 / 合法 side-effect terminal / 合法隐式 join / 非法孤岛节点），断言校验结果；当前应红；证据 `artifacts/214.2/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/workflow/validation -q` 全绿；证据 `artifacts/214.2/unit.txt`
- [ ] Frontend Unit：`rtk npm --prefix frontend run test:unit -- canvas-validation` 全绿；证据 `artifacts/214.2/frontend-unit.txt`
- [ ] frontend rem：若校验提示 UI 调整 `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`；证据 `artifacts/214.2/rem.txt`
- [ ] E2E：`rtk node frontend/e2e/workflow-condition-branch-endpoints.mjs`、`rtk node frontend/e2e/workflow-condition-branch-values.mjs` 全绿；证据 `artifacts/214.2/e2e.txt`
- [ ] Browser UAT：在画布上拖一个非法孤岛节点，校验报错可见；证据 `artifacts/214.2/uat.md` + `screenshots/`
- [ ] Git commit：`feat(workflow): canvas validates DAG topology categories`

## Slice 214.3 — Runtime data model selected/skipped state (single-path execution preserved)

- [ ] RED：写 `tests/contract/runtime_dag/test_branch_multi_target.py`、`test_skipped_does_not_block_join.py`；断言 node state graph 含 selected/skipped/pending/waiting；当前应红；证据 `artifacts/214.3/red.txt`
- [ ] GREEN：Alembic migration 新增 `runtime_node_run.selection_state` 字段并 backfill；runtime engine 在 build 阶段计算 selected / skipped，但执行仍走单路径
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/214.3/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/214.3/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿；证据 `artifacts/214.3/contract.txt`
- [ ] Docs：在 dag-semantics.md 补 "node selection state lifecycle" 小节
- [ ] Git commit：`feat(runtime): record DAG selection state without changing execution order`

## Slice 214.4 — Final output rules (Chatflow visible reply / Workflow side-effect-only)

- [ ] RED：写 `tests/contract/workflow/test_workflow_no_final_output.py` 与 `tests/integration/chatflow/test_final_output_rules.py`，覆盖 End 优先 / answer mapping / priority / side-effect-only 四种情形；当前应红；证据 `artifacts/214.4/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/chatflow -q` 全绿；证据 `artifacts/214.4/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/workflow -q` 全绿；证据 `artifacts/214.4/contract.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-execute-workflow-node.mjs`、`rtk node frontend/e2e/workflow-six-node-matrix.mjs` 全绿；证据 `artifacts/214.4/e2e.txt`
- [ ] Docs：在 dag-semantics.md 增补 "final output rules"
- [ ] Git commit：`feat(runtime): codify chatflow visible reply and workflow side-effect-only output`

## Slice 214.5 — Regression on spec 212 + 213 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：spec 212.5 + 213.6 全套命令重跑；证据 `artifacts/214.5/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212 入口 UAT 集 全绿；证据 `artifacts/214.5/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 214 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 214 exit regression`
