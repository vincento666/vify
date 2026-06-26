# Tasks — Spec 216

证据根目录：`artifacts/slices/216-chatflow-sop-compat-on-dag/<slice>/`

## Slice 216.1 — Chatflow interrupt / resume under DAG

- [ ] RED：写 `tests/integration/chatflow/test_resume_no_replay_side_effect.py` 和 `tests/contract/runtime/test_waiting_node_set.py`，断言 resume 只恢复 waiting 节点 + waiting 集合可多元素；当前应红；证据 `artifacts/216.1/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/chatflow -q` 全绿；证据 `artifacts/216.1/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/chatflow -q` 全绿；证据 `artifacts/216.1/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-information-collection.mjs`、`rtk node frontend/e2e/chatflow-message-question-input.mjs`、`rtk node frontend/e2e/chatflow-transfer-to-human-node.mjs`、`rtk node frontend/e2e/chatflow-resume-reliability.mjs` 全绿；证据 `artifacts/216.1/e2e.txt`
- [ ] Browser UAT：信息收集 + 转人工组合，截图 waiting 节点集合显示；证据 `artifacts/216.1/uat.md`
- [ ] Git commit：`feat(chatflow): expose waitingNodes set and prevent side-effect replay on resume`

## Slice 216.2 — Chatflow final reply rules under multi-path

- [ ] RED：写 `tests/integration/chatflow/test_final_reply_rules.py`，覆盖 End 优先 / answer mapping / priority / side-effect-only 结构化执行摘要 四组 case；当前应红；证据 `artifacts/216.2/red.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_dag -q` 不回归；证据 `artifacts/216.2/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/chatflow -q` 全绿；证据 `artifacts/216.2/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-channels.mjs`、`rtk node frontend/e2e/chatflow-execute-workflow-node.mjs` 全绿；证据 `artifacts/216.2/e2e.txt`
- [ ] Docs：在 dag-semantics.md 增补 "Chatflow final reply selection"
- [ ] Git commit：`feat(chatflow): codify final reply selection across DAG paths`

## Slice 216.3 — SOP Router ledger schema enforced & aggregated views

- [ ] RED：写 `tests/unit/runtime_lab/test_sop_router_ledger_schema.py` 升级版与 `tests/integration/runtime_lab/test_no_state_mirroring.py`、`tests/contract/runtime_lab/test_aggregate_from_child_chatflow.py`，断言 ledger 仅保存白名单字段，且 `current_step / pending_prompt / collected / scoped_variables / checkpoint / node events / run status` 从 child Chatflow 聚合；当前应红；证据 `artifacts/216.3/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime_lab -q` 全绿；证据 `artifacts/216.3/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_lab -q` 全绿；证据 `artifacts/216.3/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_lab -q` 全绿；证据 `artifacts/216.3/contract.txt`
- [ ] Docs：在 `docs/chatflow-sop-state-boundary.md` 更新最终字段集
- [ ] Git commit：`refactor(runtime-lab): enforce SOP ledger whitelist and aggregate child Chatflow facts`

## Slice 216.4 — SOP UAT 12-case matrix

- [ ] RED：枚举 12 条 case；现有 e2e 缺哪些 fixture 写下来；当前应红；证据 `artifacts/216.4/red.txt`
- [ ] Fixture：在 `frontend/e2e/fixtures/sop-matrix/` 或 `tests/fixtures/sop_matrix/` 补 12 套 Chatflow + SOP fixture
- [ ] E2E：`rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs` 以及矩阵子脚本（如 `frontend/e2e/sop-matrix-*.mjs` 新增）全绿；证据 `artifacts/216.4/e2e.txt`
- [ ] Browser UAT：12 条 case 每条记录 API 响应 + 事件流 + 任务面板 + 刷新恢复 四维度截图；证据 `artifacts/216.4/uat.md` + `screenshots/`
- [ ] Docs：在 baseline.md 增补 "SOP 12-case matrix completed"
- [ ] Git commit：`test(uat): cover SOP 12-case matrix on DAG runtime`

## Slice 216.5 — Customer-assistant worker state machine consumption

- [ ] RED：写 `tests/integration/customer_assistant/test_worker_state_machine.py`，断言 worker 正确消费 running / waiting / completed / failed / cancelled 五状态；当前应红；证据 `artifacts/216.5/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/customer_assistant -q` 全绿；证据 `artifacts/216.5/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs` 全绿；证据 `artifacts/216.5/e2e.txt`
- [ ] Browser UAT：触发 cancel / failed 状态，截图任务面板状态展示；证据 `artifacts/216.5/uat.md`
- [ ] Git commit：`feat(customer-assistant): worker consumes full runtime state machine`

## Slice 216.6 — Regression on spec 212-215 entry gates

- [ ] Unit / Integration / Contract / Frontend / rem：四 spec 入口套件重跑全绿；证据 `artifacts/216.6/{unit,integration,contract,frontend-unit,rem}.txt`
- [ ] Browser UAT：spec 212.5 + 214.5 + 215.7 全套；证据 `artifacts/216.6/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 216 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 216 exit regression`
