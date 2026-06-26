# Tasks — Spec 217

证据根目录：`artifacts/slices/217-runtime-v2-node-compatibility-matrix/<slice>/`

## Slice 217.1 — Node compatibility matrix doc & auto scan

- [ ] RED：写 `tests/unit/runtime/test_node_executor_registry.py`，断言所有一等节点类型都在 v2 registry 中；当前应红；证据 `artifacts/217.1/red.txt`
- [ ] GREEN：新增 `docs/runtime/node-compatibility-matrix.md`，并在 `app/modules/runtime/api/node_registry.py`（如缺则新增）列出所有 executor 映射
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/217.1/unit.txt`
- [ ] Docs：matrix 覆盖 LLM / Knowledge / Agent / API / Tool / Execute Workflow / Message / Question / Information Collection / Intent / Branch / Transform / End / Start / Transfer-to-human / Aggregation / Assignment / Variable / Code 等
- [ ] Git commit：`docs(runtime): publish node compatibility matrix and registry`

## Slice 217.2 — LLM / Knowledge / Agent nodes under DAG concurrency

- [ ] RED：写 `tests/integration/runtime/nodes/test_llm_concurrent.py`、`test_knowledge_concurrent.py`、`test_agent_concurrent.py`，断言 3 节点并发跑互不串扰 + node run / event 完整；当前应红；证据 `artifacts/217.2/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime/nodes -q` 全绿；证据 `artifacts/217.2/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime/nodes -q` 全绿；证据 `artifacts/217.2/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/workflow-chatflow-llm-run.mjs`、`rtk node frontend/e2e/workflow-knowledge-condition-run.mjs`、`rtk node frontend/e2e/workflow-agent-call-node.mjs` 全绿；证据 `artifacts/217.2/e2e.txt`
- [ ] Git commit：`feat(runtime-nodes): validate LLM/Knowledge/Agent under DAG concurrency`

## Slice 217.3 — API / Tool / Execute Workflow nodes under DAG concurrency

- [ ] RED：写 `tests/integration/runtime/nodes/test_api_concurrent.py`、`test_tool_concurrent.py`、`test_execute_workflow_concurrent.py`；当前应红；证据 `artifacts/217.3/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime/nodes -q` 全绿；证据 `artifacts/217.3/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime/nodes -q` 全绿；证据 `artifacts/217.3/contract.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-execute-workflow-node.mjs`、`rtk node frontend/e2e/workflow-transform-nodes.mjs`、`rtk node frontend/e2e/workflow-six-node-matrix.mjs` 全绿；证据 `artifacts/217.3/e2e.txt`
- [ ] Git commit：`feat(runtime-nodes): validate API/Tool/Execute Workflow under DAG concurrency`

## Slice 217.4 — Side-effect node idempotency & proposed action protection

- [ ] RED：写 `tests/contract/runtime/nodes/test_side_effect_idempotency.py`，覆盖消息发送 / 写库 / 转人工 / 调用外部 API 4 类 case，断言重试不会重复写；当前应红；证据 `artifacts/217.4/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime/nodes -q` 全绿；证据 `artifacts/217.4/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime/nodes -q` 全绿；证据 `artifacts/217.4/contract.txt`
- [ ] Docs：在 node-compatibility-matrix.md 把 side-effect 节点的"幂等键 / 执行记录 / proposed action"列填齐
- [ ] Git commit：`feat(runtime-nodes): require idempotency or proposed action on side-effect nodes`

## Slice 217.5 — Compatibility check pushes invalid config to edit/start time

- [ ] RED：写 `tests/unit/workflow/validation/test_compatibility_errors.py`，覆盖 5 类典型非法配置（缺端口 / 缺 schema / 不支持的字段组合 / 引用不存在变量 / 节点版本不兼容）；当前应红；证据 `artifacts/217.5/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/workflow/validation -q` 全绿；证据 `artifacts/217.5/unit.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/workflow -q` 不回归；证据 `artifacts/217.5/contract.txt`
- [ ] Code search：在 runtime 调度路径下 grep `unsupported`，断言 0 命中；证据 `artifacts/217.5/grep-unsupported.txt`
- [ ] E2E：`rtk node frontend/e2e/workflow-six-node-matrix.mjs` 在非法配置时显示可读错误；证据 `artifacts/217.5/e2e.txt`
- [ ] Git commit：`feat(workflow): surface invalid node config at compatibility check`

## Slice 217.6 — Chatflow / Workflow capability parity table

- [ ] RED：写 `tests/contract/runtime/nodes/test_capability_parity.py`，比较 Chatflow 与 Workflow 同类节点 capability schema；当前应红；证据 `artifacts/217.6/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime/nodes -q` 全绿；证据 `artifacts/217.6/contract.txt`
- [ ] Docs：在 node-compatibility-matrix.md 增加 "Chatflow / Workflow parity" 表，注明明确产品差异
- [ ] Git commit：`docs(runtime): document Chatflow/Workflow node parity table`

## Slice 217.7 — Regression on spec 212-216 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：五 spec 入口套件重跑全绿；证据 `artifacts/217.7/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212.5 + 214.5 + 215.7 + 216.6 全套；证据 `artifacts/217.7/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 217 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 217 exit regression`
