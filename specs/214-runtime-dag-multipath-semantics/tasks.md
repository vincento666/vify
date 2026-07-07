# Tasks — Spec 214

证据根目录：`artifacts/slices/214-runtime-dag-multipath-semantics/<slice>/`

## Slice 214.1 — DAG semantics doc & Pydantic schema

- [x] RED：写 `tests/contract/runtime_dag/test_dag_schema.py`，断言 `EdgeSpec / PortSpec / BranchGroupSpec / NodeSelectionState / FinalOutputRule` 等模型存在并满足约定字段；当前应红；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.1/red.txt`
- [x] GREEN：在 `app/modules/runtime/api/schemas.py` 落实 canonical schema，并由 `app/modules/workflow/api/schemas.py` re-export
- [x] Unit：`rtk uv run pytest tests/unit/workflow -q` 全绿（`86 passed, 12 subtests passed`）；`tests/unit/runtime` 目录不存在，runtime schema 由 contract 覆盖；证据 `unit-workflow.txt` / `unit-runtime.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿（`5 passed`）；证据 `contract.txt`
- [x] Docs：新增 `docs/runtime/dag-semantics.md`，覆盖 edge / port / branch / skipped / terminal / final-output 全部子节；证据 `docs-check.txt`
- [x] Git commit：`feat(runtime): define DAG multipath semantics schema`

## Slice 214.2 — Canvas validation: fan-out, branch, side-effect terminal, implicit join, island

- [x] RED：写 `tests/unit/workflow/validation/test_dag_canvas_rules.py`，准备合法 fan-out / 合法多分支 / 合法 side-effect terminal / 合法隐式 join / 非法孤岛节点，并补充 ambiguous default fan-out；当前红于 fan-out / terminal / island；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.2/red.txt`
- [x] Unit：`rtk uv run pytest tests/unit/workflow/validation -q` 全绿（`6 passed`）；补跑 `tests/unit/workflow -q` 全绿（`92 passed, 12 subtests passed`）；证据 `unit.txt` / `unit-workflow-full.txt`
- [x] Frontend Unit：`rtk npm --prefix frontend run test:unit -- canvas-validation` 全绿（`4 passed`）；补跑完整前端 unit 全绿（`99 passed`, `431 passed`）；证据 `frontend-unit.txt` / `frontend-unit-full.txt`
- [x] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` 全绿（`1 passed`）；证据 `rem.txt`
- [x] E2E：`rtk node frontend/e2e/workflow-condition-branch-endpoints.mjs`、`rtk node frontend/e2e/workflow-condition-branch-values.mjs` 全绿；证据 `e2e.txt`
- [x] Browser UAT：在画布上添加/拖连一个非法孤岛节点，校验报错可见；证据 `uat.md` + `screenshots/island-validation.png`
- [x] Git commit：`feat(workflow): canvas validates DAG topology categories`

## Slice 214.3 — Runtime data model selected/skipped state (single-path execution preserved)

- [x] RED：写 `tests/contract/runtime_dag/test_branch_multi_target.py`、`test_skipped_does_not_block_join.py`；断言 node state graph 含 selected/skipped/pending/waiting；当前红于缺少 `app.modules.runtime.domain` / selection builder；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.3/red.txt`
- [x] GREEN：Alembic migration 新增实际 runtime node-run 存储表 `workflow_node_run.selection_state` 字段并 backfill；新增 runtime DAG selection builder 计算 selected / skipped / pending / waiting；runtime v2 继续按 `_next_node_key` 单路径执行
- [x] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿（`1 passed`）；补跑 workflow runtime unit 全绿（`14 passed, 6 subtests passed`）和 workflow 全量 unit（`93 passed, 12 subtests passed`）；证据 `unit.txt` / `unit-workflow-runtime.txt` / `unit-workflow-full.txt`
- [x] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿（`6 passed, 1 warning`）；补跑 runtime v2 node coverage pack1（`6 passed, 1 warning`）和 shared core（`3 passed, 1 warning`）；证据 `integration.txt` / `integration-workflow-runtime-v2.txt` / `integration-shared-core.txt`
- [x] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 全绿（`8 passed`）；证据 `contract.txt`
- [x] Docs：在 dag-semantics.md 补 "Node Selection State Lifecycle" 小节；证据 `docs-check.txt`
- [x] Git commit：`feat(runtime): record DAG selection state without changing execution order`

## Slice 214.4 — Final output rules (Chatflow visible reply / Workflow side-effect-only)

- [x] RED：写 `tests/contract/workflow/test_workflow_no_final_output.py` 与 `tests/integration/chatflow/test_final_output_rules.py`，覆盖 End 优先 / answer mapping / priority / side-effect-only 四种情形；红于 answer mapping / priority / no-reply summary / Workflow summary（`4 failed, 1 passed`）；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.4/red.txt`
- [x] Unit：`rtk uv run pytest tests/unit/workflow/test_runtime_v2_core.py -q` 全绿（`7 passed, 6 subtests passed`）；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.4/unit.txt`
- [x] Integration：`rtk uv run pytest tests/integration/chatflow -q` 全绿（`4 passed, 1 warning`）；补跑 runtime-v2 facade 回归全绿（`10 passed, 1 warning`）；证据 `integration.txt` / `integration-runtime-v2-regression.txt`
- [x] Contract：`rtk uv run pytest tests/contract/workflow -q` 全绿（`1 passed, 1 warning`）；补跑 run gateway 与 runtime DAG 合约全绿；证据 `contract.txt` / `contract-gateway-regression.txt` / `contract-runtime-dag.txt`
- [x] E2E：`rtk node frontend/e2e/chatflow-execute-workflow-node.mjs`、`rtk node frontend/e2e/workflow-six-node-matrix.mjs` 全绿；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.4/e2e.txt`
- [x] Browser UAT：Playwright Chromium 真实页面执行并保存截图；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.4/uat.md`
- [x] Docs：在 dag-semantics.md 增补 final output rule 解析和 side-effect-only summary shape
- [x] Git commit：`feat(runtime): codify chatflow visible reply and workflow side-effect-only output`

## Slice 214.5 — Regression on spec 212 + 213 entry gates

- [x] RED：SOP scale 红于 `group_booking` 等待 `COMPLETE_TASK`，并补 runtime result `sessionId` 契约红测；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/red-sop-scale.txt` / `red-runtime-result-session-id.txt`
- [x] Unit / Integration / Contract / Frontend / rem：spec 212.5 + 213.6 全套命令重跑；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/{unit,integration,contract,frontend-unit,rem}.txt`
- [x] Browser UAT：spec 212 入口 UAT 集全绿；证据 `artifacts/slices/214-runtime-dag-multipath-semantics/214.5/uat.md`
- [x] Docs：在 baseline.md 追记 "spec 214 exit @ SHA <sha>"
- [x] Git commit：`test(runtime): seal spec 214 exit regression` (`a120f00bb505797a9e569527d9220ec1abf4f7c9`)
