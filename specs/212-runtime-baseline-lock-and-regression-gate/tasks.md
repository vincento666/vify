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
