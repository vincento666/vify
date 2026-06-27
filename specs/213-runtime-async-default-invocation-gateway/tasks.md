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

> 起源：slice 213.2 把"默认 async durable"用 contract 锁定后，e2e `chatflow-run-optimistic-loading.mjs` 整脚本验证暴露其 mock 锁在 `/api/v1/chatflows/{id}/runs-legacy`，但 production frontend 已经从 `/runs-legacy` 切到默认 async `/runs`。`git stash` 在 HEAD `4201a220` 复跑确认该 fail 与 213.2 改动**无关**——production 路径迁移在更早时间已发生，e2e 的 mock URL 没跟上。
>
> 范围：仅修 mock URL 配置（`page.route("**/api/v1/chatflows/*/runs-legacy", ...)` → 命中默认 async `/runs`）。**不动 e2e 的断言语义** — `runRequestSeen` 断言保留，optimistic-loading bubble 检测保留。

- [ ] RED：重跑 `chatflow-run-optimistic-loading.mjs`，固化失败日志和"mock URL 永不命中"证据；证据 `artifacts/213.2.1/red.txt`
- [ ] 静态定位：grep 脚本中 `runs-legacy` 出现处，确认是 mock 配置而非业务断言
- [ ] Fix：把 mock URL 从 `/runs-legacy` 改为默认 async `/runs`；不动其它 mock / 断言 / step
- [ ] E2E：`rtk env HIFY_E2E_BASE_URL=http://localhost:5173 /opt/homebrew/bin/node frontend/e2e/chatflow-run-optimistic-loading.mjs` PASS；证据 `artifacts/213.2.1/e2e.txt`
- [ ] Browser UAT：留 optimistic-loading bubble 在 in-flight async request 期间可见的截图；证据 `artifacts/213.2.1/uat.md` + `screenshots/`
- [ ] frontend rem：不涉视觉尺寸（仅 mock 配置）→ 跳过 rem，记录 N/A
- [ ] Backend gates 不回归（不该有任何后端变化，但 spot check）：`rtk uv run pytest tests/integration -q` 全绿
- [ ] Docs：baseline.md 追加 "chatflow-run-optimistic-loading mock URL refresh → GREEN @ slice 213.2.1"
- [ ] Git commit：`fix(e2e): refresh chatflow-run-optimistic-loading mock to default async /runs`
- [ ] 范围保护：仅改 mock URL；若发现 e2e 还需要修业务断言才能跑通 → STOP 升级

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
