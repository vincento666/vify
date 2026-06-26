# Tasks — Spec 212

每个 slice 列其门禁清单和证据路径。证据根目录统一为 `artifacts/slices/212-runtime-baseline-lock-and-regression-gate/<slice>/`，下文简写为 `artifacts/<slice>/`。

## Slice 212.0 — Drop `PYTHONPATH=.` requirement for contract suite

- [ ] RED：在未改 `pyproject.toml` 前执行 `rtk uv run pytest tests/contract -q`，记录 collection error；证据 `artifacts/212.0/red.txt`
- [ ] GREEN：在 `pyproject.toml` 增加 `[tool.pytest.ini_options].pythonpath = ["."]`
- [ ] Unit：`rtk uv run pytest tests/unit -q` 全绿；证据 `artifacts/212.0/unit.txt`
- [ ] Contract：`rtk uv run pytest tests/contract -q` 全绿且不带 `PYTHONPATH=` 前缀；证据 `artifacts/212.0/contract.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 不回归；证据 `artifacts/212.0/integration.txt`
- [ ] Docs：在 `docs/testing/acceptance-gates.md` 把 contract gate 命令从 `PYTHONPATH=. uv run pytest tests/contract` 改为 `rtk uv run pytest tests/contract -q`
- [ ] Git commit：`chore(testing): add pytest pythonpath for contract suite`

## Slice 212.1 — Fix customer-assistant-chatflow-runtime-gateway-uat operator-task-ledger row visibility

- [ ] RED：重放 `rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs`，固化 L124 上 `refund_ticket` 行不可见的 failure 截图与日志；证据 `artifacts/212.1/red.txt` + `artifacts/212.1/screenshots/red-*.png`
- [ ] Unit：定位根因；若属后端事件 publisher，补 `rtk uv run pytest tests/unit/customer_assistant -q` 红测；若属前端轮询条件，补 `rtk npm --prefix frontend run test:unit -- operator-task-ledger` 红测；证据 `artifacts/212.1/unit.txt`
- [ ] Integration/Contract：相关 customer-assistant gateway 套件全绿；证据 `artifacts/212.1/integration.txt`
- [ ] E2E（scope: ledger row）：重放 `rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs` 必须越过 L124（`refund_ticket` 行在 15s 内可见）；脚本若在 L124 之后的行（如 L148）出现新的、与 ledger 行可见性无关的失败，记入 slice 212.6 而不阻塞 212.1；证据 `artifacts/212.1/e2e.txt`
- [ ] Browser UAT：人工 / Chrome-MCP 复跑同一脚本，留 `refund_ticket` 行可见的截图；证据 `artifacts/212.1/uat.md` + `screenshots/`
- [ ] Docs：在 baseline.md 标注 LOGIC-RED → GREEN 的迁移
- [ ] Git commit：`fix(customer-assistant): stabilize operator-task-ledger refund_ticket row`

## Slice 212.2 — Fix chatflow-conversation-run Chatflow name placeholder

- [ ] RED：重放 `rtk node frontend/e2e/chatflow-conversation-run.mjs`，固化 L16 占位符不可见的 failure；证据 `artifacts/212.2/red.txt` + `artifacts/212.2/screenshots/red-*.png`
- [ ] Unit：定位是 i18n / store hydrate / route guard 哪个层失败，补 `rtk npm --prefix frontend run test:unit -- chatflow-conversation-run` 红测；证据 `artifacts/212.2/unit.txt`
- [ ] frontend rem：若涉视觉尺寸调整，`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` 全绿；证据 `artifacts/212.2/rem.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-conversation-run.mjs` 全绿；证据 `artifacts/212.2/e2e.txt`
- [ ] Browser UAT：留入口页 Chatflow 名称占位符可见的截图；证据 `artifacts/212.2/uat.md`
- [ ] Docs：baseline.md 同步状态
- [ ] Git commit：`fix(chatflow): restore conversation-run Chatflow name placeholder`

## Slice 212.3 — Chrome-MCP harness convention in acceptance-gates.md

- [ ] RED：grep `acceptance-gates.md` 当前无 Chrome-MCP harness 调用约定章节，记录为 doc 缺口；证据 `artifacts/212.3/red.txt`
- [ ] Docs：在 `docs/testing/acceptance-gates.md` 增补 "Chrome-MCP UAT Harness" 小节，定义：脚本入口约定、headless / headful 切换、screenshot 落盘路径、日志归档、判定关键字（PASS / LOGIC-RED / ENV-BLOCKED-CHROME-MCP / ENV-BLOCKED-PGVECTOR）
- [ ] Cross-reference：在 `specs/212-*/spec.md` 验收门禁映射表引用新章节
- [ ] Git commit：`docs(testing): define chrome-mcp uat harness convention`

## Slice 212.4 — pgvector-dependent UAT subset replay

- [ ] RED：在 postgres 5432 起来前 grep 所有依赖 pgvector 的 e2e 脚本列表（`rg -l "pgvector\|vector_database\|embedding"` 之类），记录无法跑的脚本数量；证据 `artifacts/212.4/red.txt`
- [ ] Env prep：在本地启动 postgres 5432 + pgvector extension（命令记录在 uat.md，不入仓 Dockerfile）
- [ ] Browser UAT：跑 `knowledge-faq-retrieval`、`workflow-knowledge-condition-run`、相关 RAG UAT 子集；证据 `artifacts/212.4/uat.md` + `screenshots/`
- [ ] Docs：把 ENV-BLOCKED-PGVECTOR 改为 PASS（或单独升级未通过的脚本）
- [ ] Git commit：`test(uat): record pgvector-dependent uat replay evidence`

## Slice 212.5 — Full baseline replay → ALL GREEN entry gate

- [ ] Unit：`rtk uv run pytest tests/unit -q` 全绿；证据 `artifacts/212.5/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 全绿；证据 `artifacts/212.5/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract -q` 全绿；证据 `artifacts/212.5/contract.txt`
- [ ] Frontend unit：`rtk npm --prefix frontend run test:unit` 全绿；证据 `artifacts/212.5/frontend-unit.txt`
- [ ] Frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` 全绿；证据 `artifacts/212.5/rem.txt`
- [ ] Browser UAT：Chatflow 核心 7 项 + SOP 完整矩阵 + Workflow 核心 7 项 全绿；证据 `artifacts/212.5/uat.md` + `screenshots/`
- [ ] Docs：把 `baseline.md` 顶部加 "ALL GREEN @ SHA <new-sha>" 标记，并冻结
- [ ] Git commit：`test(baseline): seal 212.5 all-green entry gate for spec 213+`

## Slice 212.6 — Fix customer-assistant gateway chatflowSession on second turn

> 起源：slice 212.1 把 L124 ledger 可见性修复后，`frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs:148` 暴露出第二轮 POST `/api/v1/customer-assistant/sessions/{sid}/messages` 响应中 `chatflowSession: null`，断言 `session second turn should expose chatflow gateway mode` 失败。Baseline 时被 L124 timeout 掩盖。属于 customer-assistant gateway 第二轮响应字段问题，与 ledger 视图无关。

- [ ] RED：重放 `rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs`，固化 L148 失败日志与第二轮响应 payload；证据 `artifacts/212.6/red.txt`
- [ ] Unit/Integration/Contract：定位根因后写红测，常见是 `app/modules/customer_assistant/web/router.py` 或 `app/modules/customer_assistant/domain/service.py` 在二轮 message 路径上未填充 `chatflowSession`；证据 `artifacts/212.6/{unit,integration,contract}.txt`
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs` 整脚本全绿；证据 `artifacts/212.6/e2e.txt`
- [ ] Browser UAT：留二轮响应包含 `chatflowSession` 字段的截图或 JSON 摘录；证据 `artifacts/212.6/uat.md`
- [ ] Docs：baseline.md 追加 "L148 chatflowSession second-turn → GREEN @ slice 212.6"
- [ ] Git commit：`fix(customer-assistant): expose chatflowSession on gateway second-turn response`

## Slice 212.7 — Restore Ant-migration selector contract for chatflow-conversation-run UAT

> 起源：slice 212.2 修复 L16 placeholder=`Chatflow 名称` 后，`frontend/e2e/chatflow-conversation-run.mjs` 暴露同一个 Vue 文件 `WorkflowCreate.vue` 上 Ant Design composer 迁移（commit `29aca2d4`）遗留的 3 处 selector 漂移：
> - L27 `getByTestId('chatflow-run-fields-toggle')` — "对话设置" popover 触发器丢失 testid
> - L28 `getByPlaceholder('发送消息')` — composer 输入框 placeholder 被改为 `输入问题，可通过 shift + enter 换行`
> - L45 `getByRole('button', { name: '重置会话' })` — 重置按钮文本被改为 `清空对话`（aria-label）
> 三者同源、同文件、同 commit、同消费方 → 作为一个 root cause（"Ant 迁移未维护 e2e selector 契约"）bundle 在同一 slice。

- [ ] RED：重放 `rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-conversation-run.mjs`，固化 L27 失败日志（L28/L45 在 L27 修后逐步暴露，作为 in-slice red 续档）；证据 `artifacts/212.7/red.txt`
- [ ] Frontend Unit：在 `workflowCreateAntMigration.test.ts` 新增 3 个 test case 分别 pin L27 testid、L28 placeholder、L45 button name 契约，先红后绿；证据 `artifacts/212.7/{unit-red,unit-green}.txt`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` 全绿；证据 `artifacts/212.7/rem.txt`
- [ ] Frontend unit 全套：`rtk npm --prefix frontend run test:unit -- --reporter verbose` 不回归；证据 `artifacts/212.7/frontend-unit.txt`
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-conversation-run.mjs` 整脚本 PASS；证据 `artifacts/212.7/e2e.txt`
- [ ] Browser UAT：留 placeholder/testid/button 三处均可见的截图；证据 `artifacts/212.7/uat.md` + `screenshots/`
- [ ] Docs：baseline.md 追加 "chatflow-conversation-run L27/L28/L45 → GREEN @ slice 212.7"
- [ ] Git commit：`fix(chatflow): restore Ant-migration selector contract for conversation-run UAT`
- [ ] 范围保护：若修复过程暴露第 4+ 个隐藏 fail（不在 L27/L28/L45 列表内）→ STOP 升级到新 slice 212.8，不在本 slice 内扩范围

## Slice 212.8 — Fix chatflow-conversation-run assistant bubble empty content (sys variable rendering)

> 起源：slice 212.7 修复 L27/L28/L45 selector 契约后，`frontend/e2e/chatflow-conversation-run.mjs:36` 暴露 `chatflow-assistant-message` 元素 innerText 为空。脚本期望发送 `查订单` 后 assistant bubble 应渲染包含 sys variable（`{{sys.query}}`、`{{sys.channel}}`、`{{global.brand}}`、`{{global.locale}}`）插值后的文本，但 innerText 为空。属 chatflow trial run 的 runtime/SSE 渲染层问题，与 selector 契约无关。

- [ ] RED：重放 `rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-conversation-run.mjs`，固化 L36 失败日志（含 assertion 行号、错误信息、actual innerText）；证据 `artifacts/212.8/red.txt`
- [ ] 定位：判断断点在前端还是后端
  - 前端：assistant bubble 组件接收 SSE token 但未渲染（v-html / v-text 绑定问题、typewriter 状态机问题）
  - 后端：chatflow trial run 没有 publish token / final answer 到 SSE stream
  - 网络：SSE channel 未 connect / 返回 500
- [ ] Unit/Integration/Frontend Unit：根因层写红测，先红后绿；证据 `artifacts/212.8/{unit-red,unit-green}.txt`
- [ ] frontend rem：若涉视觉尺寸调整，跑 remScaleClosure 全绿；证据 `artifacts/212.8/rem.txt`
- [ ] Frontend unit 全套：不回归（421+ ≥ slice 前总数）；证据 `artifacts/212.8/frontend-unit.txt`
- [ ] Backend gates：若改后端，跑 unit/integration/contract 全套不回归；证据 `artifacts/212.8/{unit,integration,contract}.txt`
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-conversation-run.mjs` 整脚本 PASS；证据 `artifacts/212.8/e2e.txt`
- [ ] Browser UAT：留 assistant bubble 含 sys variable 插值文本的截图；证据 `artifacts/212.8/uat.md` + `screenshots/`
- [ ] Docs：baseline.md 追加 "chatflow-conversation-run L36 assistant bubble → GREEN @ slice 212.8"
- [ ] Git commit：`fix(chatflow): render sys variables in conversation-run assistant bubble`
- [ ] 范围保护：若 L36 修复后脚本暴露 L37+ 新失败 → STOP 升级到新 slice 212.9，不扩范围

## Slice 212.9 — Fix chatflow-conversation-run run-input-field height 0 layout

> 起源：slice 212.8 修复 L36 后，`frontend/e2e/chatflow-conversation-run.mjs:58` 暴露 `.chatflow-profile-grid .run-input-field` 内的 `.el-input__wrapper / .el-select__wrapper` 控件 height 全为 0,0,0,0。脚本期望"run parameter controls share the same height"。可能根因：Ant 迁移后该面板默认隐藏 / display:none ancestor / 控件选择子（`.el-input__wrapper`/`.el-select__wrapper`）在 Ant Design 下已失配。

- [ ] RED：重放脚本，固化 L58 失败日志（含 actual heights、面板可见性、selector 命中数）；证据 `artifacts/212.9/red.txt`
- [ ] Frontend Unit：在 `workflowCreateAntMigration.test.ts` 加测试断言 chatflow-profile-grid 下 run-input-field 控件渲染时具备非零高度（或断言面板默认可见 + 控件选择子正确）；先红后绿；证据 `artifacts/212.9/{unit-red,unit-green}.txt`
- [ ] frontend rem：`rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts` 全绿；证据 `artifacts/212.9/rem.txt`
- [ ] Frontend unit 全套不回归：证据 `artifacts/212.9/frontend-unit.txt`
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-conversation-run.mjs` 整脚本 PASS；证据 `artifacts/212.9/e2e.txt`
- [ ] Browser UAT：留 run parameter controls 高度一致的截图；证据 `artifacts/212.9/uat.md` + `screenshots/`
- [ ] Docs：baseline.md 追加 "chatflow-conversation-run L58 run-input-field height → GREEN @ slice 212.9"
- [ ] Git commit：`fix(chatflow): restore run-input-field height in conversation-run profile grid`
- [ ] 范围保护：若 L58 修复后脚本暴露 L59+ 新失败 → STOP 升级到新 slice 212.10，不扩范围
