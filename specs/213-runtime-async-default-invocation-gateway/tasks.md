# Tasks — Spec 213

证据根目录：`artifacts/slices/213-runtime-async-default-invocation-gateway/<slice>/`

## Slice 213.1 — RuntimeInvocationGateway Protocol & six-ref DTO

- [ ] RED：在 `tests/contract/runtime_gateway/test_six_ref_dto.py`（新增）断言 gateway 返回 runId/statusRef/eventsRef/eventStreamRef/nodesRef/resultRef 六字段；`rtk uv run pytest tests/contract/runtime_gateway -q` 当前应红；证据 `artifacts/213.1/red.txt`
- [ ] GREEN：在 `app/modules/runtime/api/facade.py` 增加 `RuntimeInvocationGateway` Protocol 与 `RuntimeInvocationRefs` DTO
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q` 全绿；证据 `artifacts/213.1/unit.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_gateway -q` 全绿；证据 `artifacts/213.1/contract.txt`
- [ ] Docs：spec.md 引用六元组字段；在 `specs/211-*/stream-refs-matrix.md` 标注 213.1 已扩字段
- [ ] Git commit：`feat(runtime): define invocation gateway six-ref DTO`

## Slice 213.2 — Chatflow & Workflow debug runs default to async durable

- [ ] RED：写 `tests/integration/runtime/test_chatflow_debug_default_async.py`、`test_workflow_debug_default_async.py`，断言默认请求返回 refs 而非完成结果；当前应红；证据 `artifacts/213.2/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/runtime -q`、`tests/unit/workflow -q`、`tests/unit/chatflow -q` 全绿；证据 `artifacts/213.2/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 全绿；证据 `artifacts/213.2/integration.txt`
- [ ] Frontend Unit：相关 store / runner 迁移测试 `rtk npm --prefix frontend run test:unit -- chatflow-runner workflow-runner`；证据 `artifacts/213.2/frontend-unit.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-run-debug-deeplink.mjs`、`rtk node frontend/e2e/workflow-chatflow-llm-run.mjs`、`rtk node frontend/e2e/chatflow-run-optimistic-loading.mjs` 全绿；证据 `artifacts/213.2/e2e.txt`
- [ ] Browser UAT：核心 Chatflow / Workflow 调试页面截图 async refs 显示；证据 `artifacts/213.2/uat.md` + `screenshots/`
- [ ] frontend rem：若 runner 卡片样式调整 `rtk npm --prefix frontend run test:unit -- src/remScaleClosure.test.ts`
- [ ] Docs：在 `docs/testing/acceptance-gates.md` 增加 "default-async runtime contract" 一行
- [ ] Git commit：`feat(chatflow,workflow): default debug runs to durable async runtime`

## Slice 213.2.1 — Refresh chatflow-run-optimistic-loading mock URL

> 起源：slice 213.2 把"默认 async durable"用 contract 锁定后，e2e `chatflow-run-optimistic-loading.mjs` 整脚本验证暴露其 mock 锁在 `/api/v1/chatflows/{id}/runs-legacy`，但 production frontend `runChatflowV2` 实际调 `/api/v1/chatflows/{id}/runs-v2`。`git stash` 在 HEAD `4201a220` 复跑确认该 fail 与 213.2 改动**无关**——production 路径在更早时间已经是 `/runs-v2`，e2e 的 mock URL 没跟上。
>
> 范围：仅修 mock URL 配置（`page.route(...)` 路径），从 `/runs-legacy` 改为 `/runs-v2`。**不动 e2e 的断言语义** — `runRequestSeen` 断言保留，optimistic-loading bubble 检测保留。

- [ ] RED：重跑 `chatflow-run-optimistic-loading.mjs`，固化失败日志和"mock URL 永不命中"证据；证据 `artifacts/213.2.1/red.txt`
- [ ] 静态定位：grep 脚本中 `runs-legacy` 出现处，确认是 mock 配置而非业务断言
- [ ] Fix：把 mock URL 从 `/runs-legacy` 改为 `/runs-v2`（frontend 实际调用路径）；不动其它 mock / 断言 / step
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-run-optimistic-loading.mjs` PASS；证据 `artifacts/213.2.1/e2e.txt`
- [ ] Browser UAT：留 optimistic-loading bubble 在 in-flight async request 期间可见的截图；证据 `artifacts/213.2.1/uat.md` + `screenshots/`
- [ ] frontend rem：不涉视觉尺寸（仅 mock 配置）→ 跳过 rem，记录 N/A
- [ ] Backend gates 不回归（不该有任何后端变化，但 spot check）：`rtk uv run pytest tests/integration -q` 全绿
- [ ] Docs：baseline.md 追加 "chatflow-run-optimistic-loading mock URL refresh → GREEN @ slice 213.2.1"
- [ ] Git commit：`fix(e2e): refresh chatflow-run-optimistic-loading mock to /runs-v2`
- [ ] 范围保护：仅改 mock URL；若发现 e2e 还需要修业务断言才能跑通 → STOP 升级

## Slice 213.2.2 — Extend default-async contract to /runs-v2

> 起源：slice 213.2 的 integration test 只断言了 `POST /api/v1/{workflows,chatflows}/{id}/runs` 路径，但 backend 同时有 `/runs-v2` 路径（`run_workflow_v2` / `run_chatflow_v2` handler）。**两个 handler 代码完全相同** — 都调 `_start_workflow_runtime_v2_gateway` / `_start_chatflow_runtime_v2_gateway`，envelope shape 相同。frontend `runChatflowV2` 用的是 `/runs-v2`，所以 213.2 锁了一个无人 enforce 的入口。
>
> 本 slice 不动 production handler 代码（两条路径本就一致），仅扩 integration test 同时断言 `/runs` 和 `/runs-v2` 都 emit `runtimeMode=async-durable` + 六字段 refs，让 contract 真正覆盖 frontend 调用路径。物理统一两个 alias 延后到 213.X-unify-runs-v2。

- [ ] RED：在 `tests/integration/runtime/test_debug_runs_default_async.py` 加 2 个新 case 断言 `/runs-v2` 同样 emit `runtimeMode=async-durable` + 六字段；当前应红（test 不存在 = "未覆盖" 视为 RED）；证据 `artifacts/213.2.2/red.txt`
- [ ] GREEN：因为 `/runs-v2` handler 已经调用同一个 gateway，新测试应该直接 PASS；证据 `artifacts/213.2.2/green.txt`
- [ ] Backend gates 不回归：unit 368 / contract 101 / integration 445 + 3 (213.2) + 2 (本 slice) = 450
- [ ] Docs：在 `docs/testing/acceptance-gates.md` § Default-async runtime contract 章节追加一段："Both `/runs` and `/runs-v2` aliases serve the same async-durable handler at present; integration tests pin both paths. Physical de-duplication tracked in slice 213.X-unify-runs-v2."
- [ ] Git commit：`test(runtime): extend default-async contract to /runs-v2 alias`

## Slice 213.X-unify-runs-v2 — Retire /runs-v2 alias

> **立项时机**：spec 213 收尾（213.6 regression 之后）或独立 spec。**不阻塞** spec 213.3 / 213.4 / 213.5 / 213.6 / 213.7 推进。
>
> `/runs` 和 `/runs-v2` 两个 handler 代码完全相同，frontend 调 `/runs-v2`、backend `/runs` 同时存在等于 URL alias。物理统一：删 `run_workflow_v2` / `run_chatflow_v2` handler、frontend `runChatflowV2` 改调 `/runs`、扫描所有 e2e mock 把 `/runs-v2` 改 `/runs`。

- [ ] RED：grep 全仓 `/runs-v2`、`runs-v2`、`runChatflowV2`、`workflow_run_v2` 等关键字，列影响清单（预计 backend 2 handler、frontend 1 API client、N 个 e2e mock）；证据 `artifacts/213.X/red.txt`
- [ ] 删 backend `run_workflow_v2` 和 `run_chatflow_v2` 两个路由（保留 `_start_*_runtime_v2_gateway` 内部函数）
- [ ] 改 frontend `frontend/src/api/workflow.ts`（或同等位置）`runChatflowV2` URL `/runs-v2` → `/runs`
- [ ] 扫描所有 e2e mock：`rtk grep -rln "runs-v2" frontend/e2e/` 改成 `/runs`
- [ ] Unit / Integration / Contract 全套不回归
- [ ] Frontend unit / rem 不回归
- [ ] E2E：全部跟 chatflow/workflow 运行相关的脚本 PASS，特别是之前用 `/runs-v2` mock 的
- [ ] Browser UAT：手验 chatflow / workflow debug run 仍可正常发起
- [ ] Docs：acceptance-gates.md § Default-async runtime contract 章节去掉"two aliases"备注，spec 213.2.2 标完成
- [ ] Git commit：`refactor(runtime): retire /runs-v2 alias in favour of unified /runs`
- [ ] 范围保护：仅 URL alias 物理统一；不动 V2 invocation gateway 任何业务逻辑

## Slice 213.3 — SOP Router returns runtime refs and stops mirroring Chatflow state

- [ ] RED：写 `tests/integration/runtime_lab/test_sop_router_async_refs.py` 与 `tests/unit/runtime_lab/test_sop_router_ledger_schema.py`，断言 ledger 仅保存 conversation/active-child/suspended/route history/resume offer/intent summary 字段，并断言 SOP Router 默认调用返回 runtime refs；当前应红；证据 `artifacts/213.3/red.txt`
- [ ] GREEN：移除 SOP Router 内对 `current_step/pending_prompt/collected/scoped_variables/run status` 的写入路径，改为按需聚合 child Chatflow session/run/checkpoint
- [ ] Integration：`rtk uv run pytest tests/integration/runtime_lab -q` 全绿；证据 `artifacts/213.3/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/unified-routing-sop-chatflow-runtime-uat.mjs`、`rtk node frontend/e2e/chatflow-session-state.mjs`、`rtk node frontend/e2e/chatflow-resume-api.mjs` 全绿；证据 `artifacts/213.3/e2e.txt`
- [ ] Browser UAT：客服侧 SOP 切换 / 暂停 / 恢复场景，截图任务面板字段；证据 `artifacts/213.3/uat.md`
- [ ] Docs：在 `docs/chatflow-sop-state-boundary.md`（如缺则新增）记录 ledger 字段最终集
- [ ] Git commit：`refactor(runtime-lab): SOP Router stops mirroring Chatflow state`

## Slice 213.4 — Customer-assistant worker returns async refs by default

- [ ] RED：写 `tests/integration/customer_assistant/test_worker_default_async_refs.py`，断言默认 worker 调用 Chatflow / SOP 返回 runId + refs；当前应红；证据 `artifacts/213.4/red.txt`
- [ ] Unit：`rtk uv run pytest tests/unit/customer_assistant -q` 全绿；证据 `artifacts/213.4/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/customer_assistant -q` 全绿；证据 `artifacts/213.4/integration.txt`
- [ ] E2E：`rtk node frontend/e2e/customer-assistant-chatflow-runtime-gateway-uat.mjs`、`rtk node frontend/e2e/chatflow-transfer-to-human-node.mjs` 全绿；证据 `artifacts/213.4/e2e.txt`
- [ ] Docs：在 `docs/customer-assistant-runtime.md`（如缺则新增）记录默认 async refs 行为与 `--sync` 显式 fallback
- [ ] Git commit：`feat(customer-assistant): worker defaults to async runtime refs`

## Slice 213.5 — Disconnect recovery via runId returns status/events/nodes/result

- [ ] RED：写 `tests/contract/runtime_recovery/test_runid_recovery.py`，断言通过 runId 可在断线后重建 status / events (afterSequence=N) / nodes / result；当前应红；证据 `artifacts/213.5/red.txt`
- [ ] Integration：`rtk uv run pytest tests/integration/runtime -q` 不回归；证据 `artifacts/213.5/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract/runtime_recovery -q` 全绿；证据 `artifacts/213.5/contract.txt`
- [ ] E2E：`rtk node frontend/e2e/chatflow-resume-reliability.mjs`、`rtk node frontend/e2e/chatflow-resume-api.mjs` 全绿；证据 `artifacts/213.5/e2e.txt`
- [ ] Docs：在 `specs/211-*/stream-refs-matrix.md` 增加 "recovery" 列
- [ ] Git commit：`test(runtime): cover runId-based disconnect recovery`

## Slice 213.6 — Regression on spec 212 entry gates

- [ ] Unit：`rtk uv run pytest tests/unit -q` 全绿；证据 `artifacts/213.6/unit.txt`
- [ ] Integration：`rtk uv run pytest tests/integration -q` 全绿；证据 `artifacts/213.6/integration.txt`
- [ ] Contract：`rtk uv run pytest tests/contract -q` 全绿；证据 `artifacts/213.6/contract.txt`
- [ ] Frontend unit / rem：`rtk npm --prefix frontend run test:unit` 和 `... src/remScaleClosure.test.ts` 全绿；证据 `artifacts/213.6/frontend-unit.txt`、`rem.txt`
- [ ] Browser UAT：spec 212.5 整套脚本全绿；证据 `artifacts/213.6/uat.md`
- [ ] Docs：在 baseline.md 追记 "spec 213 exit @ SHA <sha>"
- [ ] Git commit：`test(runtime): seal spec 213 exit regression`
